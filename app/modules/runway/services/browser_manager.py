"""Singleton-ish Playwright browser context reused across scraper requests.

Lazy-init on first use, explicit shutdown via FastAPI lifespan. A single
BrowserContext is kept alive because loading storage_state + running cold-start
navigation on every request is slow and makes session expiry harder to detect.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.core.config import settings

_log = logging.getLogger("runway.browser")


# Lightweight stealth evasions. Not a full replacement for
# playwright-stealth but covers the most common webdriver/automation fingerprint
# checks. Extend if Runway starts flagging us.
_STEALTH_INIT_SCRIPT = """
(() => {
  try {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  } catch (e) {}
  try {
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
    });
  } catch (e) {}
  try {
    Object.defineProperty(navigator, 'plugins', {
      get: () => [
        { name: 'Chrome PDF Plugin' },
        { name: 'Chrome PDF Viewer' },
        { name: 'Native Client' },
      ],
    });
  } catch (e) {}
  try {
    window.chrome = window.chrome || { runtime: {} };
  } catch (e) {}
  try {
    const originalQuery = window.navigator.permissions &&
      window.navigator.permissions.query;
    if (originalQuery) {
      window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters);
    }
  } catch (e) {}
})();
"""


class RunwayBrowserManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._storage_fingerprint: str | None = None

    async def ensure_started(self, storage_state: dict[str, Any] | None) -> None:
        fingerprint = _fingerprint(storage_state)
        async with self._lock:
            # Re-start if storage_state changed (user re-logged in).
            if self._context is not None and self._storage_fingerprint != fingerprint:
                _log.info("storage_state changed, restarting browser context")
                await self._teardown()

            if self._context is not None:
                return

            _log.info(
                "launching chromium (headless=%s)",
                settings.runway_playwright_headless,
            )
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.runway_playwright_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            self._context = await self._browser.new_context(
                storage_state=storage_state,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1440, "height": 900},
            )
            await self._context.add_init_script(_STEALTH_INIT_SCRIPT)
            self._context.set_default_timeout(settings.runway_scraper_timeout_ms)
            self._storage_fingerprint = fingerprint

    async def new_page(
        self, storage_state: dict[str, Any] | None = None
    ) -> Page:
        await self.ensure_started(storage_state)
        assert self._context is not None  # for type checker
        return await self._context.new_page()

    async def shutdown(self) -> None:
        async with self._lock:
            await self._teardown()

    async def _teardown(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        except Exception as exc:
            _log.warning("context close failed: %s", exc)
        try:
            if self._browser is not None:
                await self._browser.close()
        except Exception as exc:
            _log.warning("browser close failed: %s", exc)
        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception as exc:
            _log.warning("playwright stop failed: %s", exc)
        self._context = None
        self._browser = None
        self._playwright = None
        self._storage_fingerprint = None


def _fingerprint(storage_state: dict[str, Any] | None) -> str:
    """Cheap change detector so we can rebuild context when user re-logs in."""
    if not storage_state:
        return ""
    cookies = storage_state.get("cookies") or []
    # Use count + any runway cookie value as fingerprint.
    names = sorted(c.get("name", "") for c in cookies)
    return f"{len(cookies)}:{'|'.join(names[:5])}"


# Module-level singleton. Use from dependencies.py.
browser_manager = RunwayBrowserManager()
