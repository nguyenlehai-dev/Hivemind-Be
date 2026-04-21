"""MVP Playwright scraper for app.runwayml.com /custom page.

Reuses the storage_state captured by LoginService to authenticate, then drives
the Custom UI like a human would: switch mode, upload reference, type prompt,
click Generate, wait for result, extract URL.

**Expect breakage**. Runway's DOM changes frequently; selectors in
``scraper_selectors.py`` will need periodic adjustment. See
``docs/setup-scraper.md`` for the debug workflow.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.async_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.core.config import settings
from app.modules.runway.services.browser_manager import browser_manager
from app.modules.runway.services.scraper_selectors import (
    ADVANCED_TOGGLE,
    ASPECT_RATIO_OPTION_CSS,
    CUSTOM_URL_TEMPLATE,
    DURATION_OPTION_CSS,
    ERROR_BANNER,
    GENERATE_BUTTON,
    LOGIN_URL_FRAGMENTS,
    MODEL_PICKER_SEARCH,
    MODEL_PICKER_TRIGGER,
    PROMPT_TEXTAREA,
    REFERENCE_FILE_INPUT,
    RESULT_IMAGE,
    RESULT_VIDEO,
    SEED_INPUT,
)

_log = logging.getLogger("runway.scraper")


class RunwayScraperError(Exception):
    def __init__(self, message: str, *, screenshot_path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.screenshot_path = screenshot_path


class RunwayScraperService:
    """Drive the Runway Custom UI for a single generation.

    One instance per request is fine; browser is shared via BrowserManager.
    """

    async def generate(
        self,
        *,
        mode: str,
        prompt: str,
        model_id: str = "",
        gen_settings: dict[str, Any] | None = None,
        reference_data_urls: list[str] | None = None,
        storage_state: dict[str, Any] | None,
    ) -> str:
        """Run the full flow. Returns the URL of the produced media."""
        if not settings.runway_team_slug:
            raise RunwayScraperError(
                "HIVEMIND_RUNWAY_TEAM_SLUG not set. Get it from your Runway URL: "
                "app.runwayml.com/video-tools/teams/<THIS>/ai-tools/generate",
            )

        page = await browser_manager.new_page(storage_state)
        console_logs: list[str] = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[pageerror] {err}"))
        try:
            return await self._run(
                page,
                mode=mode,
                prompt=prompt,
                model_id=model_id,
                gen_settings=gen_settings or {},
                reference_data_urls=reference_data_urls or [],
            )
        except RunwayScraperError as exc:
            path = await self._dump_debug(page, "error", console_logs)
            exc.screenshot_path = exc.screenshot_path or path
            raise
        except PlaywrightTimeoutError as exc:
            path = await self._dump_debug(page, "timeout", console_logs)
            raise RunwayScraperError(
                f"Timeout driving Runway UI: {exc}. See debug dump for DOM state.",
                screenshot_path=path,
            ) from exc
        except Exception as exc:
            path = await self._dump_debug(page, "unexpected", console_logs)
            raise RunwayScraperError(
                f"Unexpected scraper failure: {exc}",
                screenshot_path=path,
            ) from exc
        finally:
            try:
                await page.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal flow
    # ------------------------------------------------------------------

    async def _run(
        self,
        page: Page,
        *,
        mode: str,
        prompt: str,
        model_id: str,
        gen_settings: dict[str, Any],
        reference_data_urls: list[str],
    ) -> str:
        url = CUSTOM_URL_TEMPLATE.format(
            team=settings.runway_team_slug,
            tool=mode,
        )
        _log.info("scraper goto %s", url)
        await page.goto(url, wait_until="domcontentloaded")

        # If Runway bounced us to /login, storage_state is dead.
        if any(frag in page.url for frag in LOGIN_URL_FRAGMENTS):
            raise RunwayScraperError(
                "Runway redirected to /login — stored session expired. "
                "Click Connect Runway in the header to refresh the session.",
            )

        # Let React settle.
        await page.wait_for_load_state("networkidle", timeout=20_000)

        for index, data_url in enumerate(reference_data_urls):
            _log.info("uploading reference %d/%d", index + 1, len(reference_data_urls))
            await self._upload_reference(page, data_url)

        if prompt:
            await self._set_prompt(page, prompt)

        if model_id:
            await self._select_model(page, model_id)

        # Advanced settings are best-effort: fail silent if Runway UI differs.
        await self._apply_settings(page, mode, gen_settings)

        await self._click_generate(page)

        return await self._wait_for_result(page, mode)

    async def _upload_reference(self, page: Page, data_url: str) -> None:
        # Decode the base64 data URL and write to a tmp file, because
        # Playwright's set_input_files wants a path or in-memory bytes.
        kind, b64 = _split_data_url(data_url)
        content = base64.b64decode(b64)
        tmp_path = Path(f"/tmp/runway-ref-{uuid4().hex}.{_ext_from_kind(kind)}")
        # On Windows, /tmp may not exist → use tempfile fallback.
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=f".{_ext_from_kind(kind)}", delete=False
        ) as tmp:
            tmp.write(content)
            real_path = tmp.name

        file_input = await _first_match(page, REFERENCE_FILE_INPUT, timeout=5_000)
        if file_input is None:
            raise RunwayScraperError(
                "Couldn't find a file input for reference upload. "
                "Update REFERENCE_FILE_INPUT in scraper_selectors.py.",
            )
        await file_input.set_input_files(real_path)
        await asyncio.sleep(0.8)  # give the UI time to preview

    async def _set_prompt(self, page: Page, text: str) -> None:
        textarea = await _first_match(page, PROMPT_TEXTAREA, timeout=5_000)
        if textarea is None:
            raise RunwayScraperError(
                "Couldn't find prompt textarea. Update PROMPT_TEXTAREA selectors.",
            )
        await textarea.click()
        await textarea.fill(text)

    async def _select_model(self, page: Page, model_id: str) -> None:
        """Best-effort: open model picker and pick an option matching model_id.

        Silent no-op if the picker can't be found — Runway will use the default
        model currently shown. Adjust MODEL_PICKER_TRIGGER if Runway's picker
        button is labelled differently.
        """
        trigger = await _first_match(page, MODEL_PICKER_TRIGGER, timeout=3_000)
        if trigger is None:
            _log.warning("model picker trigger not found; using UI default")
            return
        await trigger.click()
        await asyncio.sleep(0.4)

        # If picker has a search box, use it.
        search = await _first_match(page, MODEL_PICKER_SEARCH, timeout=2_000)
        if search is not None:
            await search.fill(model_id)
            await asyncio.sleep(0.3)

        # Click the option matching our id/name (case-insensitive substring).
        option = page.get_by_text(model_id, exact=False).first
        try:
            await option.click(timeout=3_000)
            await asyncio.sleep(0.3)
        except PlaywrightTimeoutError:
            _log.warning("model %s not found in picker; using default", model_id)
            # Best-effort: close the picker by pressing Escape.
            await page.keyboard.press("Escape")

    async def _apply_settings(
        self, page: Page, mode: str, gen_settings: dict[str, Any]
    ) -> None:
        """Best-effort apply aspect_ratio / seed / duration.

        Runway's settings UI varies by model; we silently skip any chip that
        can't be found. If a setting fails to apply, Runway uses its default.
        """
        # Some models hide settings behind an Advanced toggle — try to open.
        toggle = await _first_match(page, ADVANCED_TOGGLE, timeout=1_500)
        if toggle is not None:
            try:
                await toggle.click(timeout=1_000)
                await asyncio.sleep(0.3)
            except PlaywrightTimeoutError:
                pass

        aspect_ratio = gen_settings.get("aspect_ratio")
        if aspect_ratio:
            selector = ASPECT_RATIO_OPTION_CSS.format(ratio=aspect_ratio)
            try:
                await page.locator(selector).first.click(timeout=1_500)
            except PlaywrightTimeoutError:
                _log.info("aspect ratio %s chip not found", aspect_ratio)

        if mode == "video":
            duration = gen_settings.get("duration") or gen_settings.get("duration_s")
            if duration:
                selector = DURATION_OPTION_CSS.format(duration=int(duration))
                try:
                    await page.locator(selector).first.click(timeout=1_500)
                except PlaywrightTimeoutError:
                    _log.info("duration %s chip not found", duration)

        seed = gen_settings.get("seed")
        if seed is not None:
            seed_input = await _first_match(page, SEED_INPUT, timeout=1_500)
            if seed_input is not None:
                try:
                    await seed_input.fill(str(int(seed)))
                except Exception as exc:
                    _log.info("seed fill failed: %s", exc)

    async def _click_generate(self, page: Page) -> None:
        btn = await _first_match(page, GENERATE_BUTTON, timeout=5_000)
        if btn is None:
            raise RunwayScraperError(
                "Couldn't find Generate button. Update GENERATE_BUTTON selectors.",
            )
        await btn.click()

    async def _wait_for_result(self, page: Page, mode: str) -> str:
        """Poll the DOM until a result media element appears or we time out."""
        if mode == "video":
            selectors = RESULT_VIDEO
        elif mode == "audio":
            # Audio result → look for video tag OR <audio> src.
            selectors = [("css", "audio[src]:not([src=''])")] + RESULT_VIDEO
        else:
            selectors = RESULT_IMAGE
        deadline_ms = settings.runway_scraper_result_wait_ms
        step = 1_500
        elapsed = 0

        while elapsed < deadline_ms:
            # Error banner?
            error_loc = await _first_match(page, ERROR_BANNER, timeout=500)
            if error_loc is not None:
                text = (await error_loc.text_content()) or "Runway reported an error"
                raise RunwayScraperError(text.strip())

            # Result ready?
            result = await _first_match(page, selectors, timeout=500)
            if result is not None:
                src = await result.get_attribute("src")
                if src and not src.startswith("blob:"):
                    _log.info("scraper result: %s", src[:80])
                    return src

            await asyncio.sleep(step / 1_000)
            elapsed += step

        raise RunwayScraperError(
            "Timed out waiting for result. Generation may still be running on "
            "Runway's side, or selectors need updating in RESULT_VIDEO/IMAGE.",
        )

    async def _dump_debug(
        self, page: Page, label: str, console_logs: list[str]
    ) -> str | None:
        """Save screenshot + HTML + console log for post-mortem."""
        try:
            Path("logs").mkdir(exist_ok=True)
            tag = f"{label}-{uuid4().hex[:8]}"
            png_path = f"logs/scraper-{tag}.png"
            html_path = f"logs/scraper-{tag}.html"
            log_path = f"logs/scraper-{tag}.log"

            try:
                await page.screenshot(path=png_path, full_page=True)
            except Exception as exc:
                _log.warning("screenshot failed: %s", exc)

            try:
                html = await page.content()
                Path(html_path).write_text(html, encoding="utf-8")
            except Exception as exc:
                _log.warning("HTML dump failed: %s", exc)

            try:
                Path(log_path).write_text(
                    f"URL: {page.url}\n\n" + "\n".join(console_logs),
                    encoding="utf-8",
                )
            except Exception:
                pass

            _log.warning("debug dump saved: logs/scraper-%s.*", tag)
            return png_path
        except Exception as exc:
            _log.warning("debug dump failed: %s", exc)
            return None


# ---- Selector helpers ----------------------------------------------------


async def _first_match(
    page: Page,
    selectors: list[tuple[str, Any]],
    *,
    timeout: int,
) -> Locator | None:
    """Try each (strategy, query) pair in order, return the first that resolves."""
    for strategy, query in selectors:
        locator = _build_locator(page, strategy, query)
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            continue
    return None


def _build_locator(page: Page, strategy: str, query: Any) -> Locator:
    if strategy == "role":
        return page.get_by_role(**query).first
    if strategy == "label":
        return page.get_by_label(query, exact=False).first
    if strategy == "placeholder":
        return page.get_by_placeholder(query, exact=False).first
    if strategy == "text":
        return page.get_by_text(query, exact=False).first
    if strategy == "test_id":
        return page.get_by_test_id(query).first
    if strategy == "css":
        return page.locator(query).first
    raise ValueError(f"Unknown selector strategy: {strategy}")


def _split_data_url(data_url: str) -> tuple[str, str]:
    """Return (mime_type, base64_payload) from 'data:mime;base64,payload'."""
    if not data_url.startswith("data:"):
        raise RunwayScraperError("Reference is not a data: URL")
    header, _, payload = data_url.partition(",")
    kind = header[5:].split(";")[0]  # 'image/png' etc.
    return kind, payload


def _ext_from_kind(kind: str) -> str:
    if "/" in kind:
        return kind.split("/")[-1].split("+")[0] or "png"
    return "png"
