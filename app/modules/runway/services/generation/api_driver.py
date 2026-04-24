from app.modules.runway.clients.runway_api import (
    RunwayAPIClient,
    RunwayAPIError,
    map_ratio,
)
from app.modules.runway.orm import GenerationRow
from app.modules.runway.repositories import AssetRepository
from app.modules.runway.schemas import GenerateRequest

# Runway API task status → our status
STATUS_MAP = {
    "PENDING": "queued",
    "THROTTLED": "queued",
    "RUNNING": "running",
    "SUCCEEDED": "completed",
    "FAILED": "failed",
    "CANCELLED": "failed",
}


def api_supports(payload: GenerateRequest, runway_api: RunwayAPIClient) -> bool:
    return (
        runway_api.is_configured
        and payload.mode == "video"
        and bool(payload.references)
    )


async def submit_api(
    payload: GenerateRequest,
    runway_api: RunwayAPIClient,
    assets: AssetRepository,
) -> tuple[str | None, str, str | None]:
    """Submit video generation to Runway Developer API.

    Returns (task_id, status, error_message).
    """
    reference = payload.references[0]
    asset = await assets.get(reference.asset_id)
    if asset is None:
        return None, "failed", f"Reference {reference.asset_id} not found"

    try:
        response = await runway_api.image_to_video(
            prompt_image=asset.preview_url,
            prompt_text=payload.prompt or "",
            ratio=map_ratio(payload.settings.aspect_ratio),
            seed=payload.settings.seed,
        )
    except RunwayAPIError as exc:
        return None, "failed", exc.message

    task_id = response.get("id")
    if not task_id:
        return None, "failed", "Runway API did not return a task id"
    return task_id, "queued", None


async def poll_runway(job: GenerationRow, runway_api: RunwayAPIClient) -> None:
    """Poll Runway task status and update the job row in-place."""
    try:
        task = await runway_api.get_task(job.external_task_id)
    except RunwayAPIError as exc:
        job.status = "failed"
        job.error = f"Runway poll failed: {exc.message}"
        return

    mapped = STATUS_MAP.get(task.get("status", ""), job.status)
    job.status = mapped

    if mapped == "completed":
        output = task.get("output") or []
        job.result_urls = [
            item if isinstance(item, str) else item.get("url")
            for item in output
            if item
        ]
    elif mapped == "failed":
        job.error = (
            task.get("failure")
            or task.get("failureCode")
            or "Runway task failed"
        )
