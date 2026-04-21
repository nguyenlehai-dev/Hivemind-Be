"""Thin wrapper around Runway's official Developer API.

Docs: https://docs.dev.runwayml.com/

We intentionally keep this minimal: only the calls we actually need for the
current generation flow (image→video + polling). Extend as needed.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class RunwayAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


# Our aspect_ratio strings → Runway ratio format (gen3a_turbo constraints).
_RATIO_MAP = {
    "16:9": "1280:768",
    "9:16": "768:1280",
    "1:1": "960:960",
    "4:3": "1280:960",
    "3:4": "960:1280",
}


def map_ratio(aspect_ratio: str) -> str:
    return _RATIO_MAP.get(aspect_ratio, "1280:768")


class RunwayAPIClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._api_key = api_key or settings.runway_api_key
        self._base_url = (base_url or settings.runway_api_base_url).rstrip("/")
        self._api_version = api_version or settings.runway_api_version
        self._timeout = timeout or settings.runway_api_timeout_s

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Runway-Version": self._api_version,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise RunwayAPIError(
                "Runway API key not configured. Set HIVEMIND_RUNWAY_API_KEY in .env.",
            )

        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json,
                )
            except httpx.HTTPError as exc:
                raise RunwayAPIError(
                    f"Runway API network error: {exc}",
                ) from exc

        if response.status_code >= 400:
            message = _extract_error_message(response)
            raise RunwayAPIError(message, status_code=response.status_code)

        return response.json()

    async def image_to_video(
        self,
        *,
        prompt_image: str,
        prompt_text: str,
        model: str | None = None,
        duration: int | None = None,
        ratio: str = "1280:768",
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Submit an image→video task. Returns {'id': task_id}."""
        body: dict[str, Any] = {
            "promptImage": prompt_image,
            "model": model or settings.runway_default_video_model,
            "ratio": ratio,
            "duration": duration or settings.runway_default_duration_s,
        }
        if prompt_text:
            body["promptText"] = prompt_text
        if seed is not None:
            body["seed"] = seed
        return await self._request("POST", "/image_to_video", json=body)

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Fetch task status. Returns the full task object."""
        return await self._request("GET", f"/tasks/{task_id}")

    async def cancel_task(self, task_id: str) -> None:
        await self._request("POST", f"/tasks/{task_id}/cancel")


def _extract_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except Exception:
        return f"Runway API error {response.status_code}: {response.text[:200]}"

    if isinstance(body, dict):
        return (
            body.get("error")
            or body.get("message")
            or f"Runway API error {response.status_code}"
        )
    return f"Runway API error {response.status_code}"
