"""Real Playwright-based login flow for Runway.

Only the login step runs in a browser. After success we extract ``storageState``
(cookies + localStorage) so subsequent requests can be made via ``httpx`` with the
same auth artefacts.

Selectors are best-effort and may need adjustment once verified against a real
Runway login page — inspect the DOM, prefer ``data-testid`` / ``role`` / labels.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

_AUTH_COOKIE_NAMES = {
    "__session",
    "__clerk_db_jwt",
    "__client",
    "runway_session",
    "auth_token",
    "session",
}


class PlaywrightLoginError(Exception):
    """Raised when the real login flow fails."""


@dataclass
class PlaywrightLoginResult:
    storage_state: dict
    landed_url: str


class PlaywrightLoginService:
    """Drive a headless Chromium session to perform the Runway login.

    This is intentionally a single-shot flow: open browser → fill form →
    wait for dashboard → dump storageState → close. No long-lived browser
    context is kept across requests.
    """

    async def login(self, email: str, password: str) -> PlaywrightLoginResult:
        if not email or not password:
            raise PlaywrightLoginError(
                "Missing Runway credentials. Set HIVEMIND_RUNWAY_EMAIL / "
                "HIVEMIND_RUNWAY_PASSWORD in .env or disable mock mode only "
                "after they are configured.",
            )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=settings.runway_playwright_headless,
            )
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(settings.runway_playwright_timeout_ms)

            try:
                await page.goto(settings.runway_login_url, wait_until="domcontentloaded")
                logger.info("runway login page loaded url=%s", page.url)
                try:
                    await self._fill_credentials(page, email, password)
                    await self._submit(page)
                    logger.info("runway login form submitted")
                except PlaywrightTimeoutError as exc:
                    logger.warning(
                        "auto-fill failed (%s); relying on manual completion in the open window",
                        exc,
                    )
                landed = await self._await_success(context, page)
                storage_state = await context.storage_state()
                return PlaywrightLoginResult(
                    storage_state=storage_state,
                    landed_url=landed,
                )
            except PlaywrightTimeoutError as exc:
                urls = [p.url for p in context.pages]
                raise PlaywrightLoginError(
                    "Timed out waiting for Runway login. Pages currently open: "
                    f"{urls}. If a Cloudflare/OAuth popup appeared, complete it "
                    "in the open window. Increase HIVEMIND_RUNWAY_PLAYWRIGHT_TIMEOUT_MS.",
                ) from exc
            finally:
                await context.close()
                await browser.close()

    async def _fill_credentials(self, page: Page, email: str, password: str) -> None:
        email_selectors = (
            'input[type="email"], input[name="email"], '
            'input[name="identifier"], input[autocomplete="username"]'
        )
        password_selectors = (
            'input[type="password"], input[name="password"]'
        )

        await page.locator(email_selectors).first.fill(email, timeout=20_000)

        # Runway uses a two-step flow (Clerk-style): email → Continue → password.
        # If password is already visible, fill both. Otherwise click Continue
        # then wait for password field.
        password_locator = page.locator(password_selectors).first
        try:
            await password_locator.wait_for(state="visible", timeout=2_000)
        except PlaywrightTimeoutError:
            await self._click_continue(page)
            await password_locator.wait_for(state="visible", timeout=30_000)

        await password_locator.fill(password, timeout=10_000)

    async def _click_continue(self, page: Page) -> None:
        for name in ("Continue", "Next", "Log in", "Sign in"):
            btn = page.get_by_role("button", name=name, exact=False).first
            try:
                await btn.click(timeout=2_000)
                return
            except PlaywrightTimeoutError:
                continue
        await page.keyboard.press("Enter")

    async def _submit(self, page: Page) -> None:
        for name in ("Log in", "Sign in", "Continue"):
            btn = page.get_by_role("button", name=name, exact=False).first
            try:
                await btn.click(timeout=5_000)
                return
            except PlaywrightTimeoutError:
                continue
        await page.keyboard.press("Enter")

    async def _await_success(self, context: BrowserContext, page: Page) -> str:
        """Poll every open page and the cookie jar until we look logged in.

        Runway may open Cloudflare/OAuth popups during login. We watch all
        pages in the context and also inspect cookies, so we detect success
        regardless of which window lands on the dashboard.
        """

        def is_logged_in_url(url: str) -> bool:
            if not url or "runwayml.com" not in url:
                return False
            lowered = url.lower()
            if any(
                seg in lowered
                for seg in (
                    "/login",
                    "/sign-in",
                    "/signin",
                    "/sign-up",
                    "/signup",
                    "/verify",
                    "/challenge",
                )
            ):
                return False
            if lowered.rstrip("/").endswith("runwayml.com"):
                return False
            return True

        timeout_s = settings.runway_playwright_timeout_ms / 1000
        deadline = time.monotonic() + timeout_s
        last_log = 0.0

        while time.monotonic() < deadline:
            for p in list(context.pages):
                if p.is_closed():
                    continue
                try:
                    url = p.url
                except Exception:
                    continue
                if is_logged_in_url(url):
                    logger.info("runway login success detected url=%s", url)
                    return url

            cookies = await context.cookies()
            auth_hits = [
                c for c in cookies
                if "runwayml.com" in c.get("domain", "")
                and c.get("name") in _AUTH_COOKIE_NAMES
            ]
            if auth_hits:
                # Cookies are set — wait briefly for any page to settle on
                # a dashboard URL, else accept the most recent runway page.
                await asyncio.sleep(1.5)
                for p in list(context.pages):
                    if p.is_closed():
                        continue
                    url = p.url
                    if "runwayml.com" in url and "/login" not in url.lower():
                        logger.info(
                            "runway auth cookies present; accepting url=%s", url,
                        )
                        return url

            now = time.monotonic()
            if now - last_log > 10:
                urls = [p.url for p in context.pages if not p.is_closed()]
                logger.info("waiting for runway login; open pages=%s", urls)
                last_log = now

            await asyncio.sleep(1)

        raise PlaywrightTimeoutError(
            f"runway login did not complete within {timeout_s:.0f}s",
        )
