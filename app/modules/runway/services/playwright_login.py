"""Real Playwright-based login flow for Runway.

Only the login step runs in a browser. After success we extract ``storageState``
(cookies + localStorage) so subsequent requests can be made via ``httpx`` with the
same auth artefacts.

Selectors are best-effort and may need adjustment once verified against a real
Runway login page — inspect the DOM, prefer ``data-testid`` / ``role`` / labels.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.core.config import settings


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
                await self._fill_credentials(page, email, password)
                await self._submit(page)
                landed = await self._await_success(page)
                storage_state = await context.storage_state()
                return PlaywrightLoginResult(
                    storage_state=storage_state,
                    landed_url=landed,
                )
            except PlaywrightTimeoutError as exc:
                raise PlaywrightLoginError(
                    "Timed out waiting for Runway login. The page layout may "
                    "have changed — update selectors in playwright_login.py "
                    "or retry with headless=False to inspect.",
                ) from exc
            finally:
                await context.close()
                await browser.close()

    async def _fill_credentials(self, page: Page, email: str, password: str) -> None:
        # Try role-based selectors first (stable across style changes), then
        # fall back to common input attributes.
        email_input = page.get_by_label("Email", exact=False).first
        password_input = page.get_by_label("Password", exact=False).first

        try:
            await email_input.fill(email, timeout=5_000)
            await password_input.fill(password, timeout=5_000)
        except PlaywrightTimeoutError:
            # Fallback selectors
            await page.locator(
                'input[type="email"], input[name="email"], input[autocomplete="username"]'
            ).first.fill(email)
            await page.locator(
                'input[type="password"], input[name="password"]'
            ).first.fill(password)

    async def _submit(self, page: Page) -> None:
        submit = page.get_by_role("button", name="Log in", exact=False).first
        try:
            await submit.click(timeout=5_000)
            return
        except PlaywrightTimeoutError:
            pass

        # Fallback: a form submit on enter.
        await page.keyboard.press("Enter")

    async def _await_success(self, page: Page) -> str:
        """Wait for dashboard navigation away from the login page."""
        prefix = settings.runway_dashboard_url_prefix.rstrip("/")
        await page.wait_for_url(
            lambda url: url.startswith(prefix) and "/login" not in url,
            timeout=settings.runway_playwright_timeout_ms,
        )
        return page.url
