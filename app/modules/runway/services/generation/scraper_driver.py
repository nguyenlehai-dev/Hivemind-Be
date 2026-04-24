from app.modules.runway.schemas import GenerateRequest
from app.modules.runway.services.scraper_runner import spawn_job


def scraper_supports(payload: GenerateRequest) -> bool:
    return payload.mode in ("image", "video", "audio")


def spawn_scraper_job(job_id: str, payload: GenerateRequest) -> None:
    """Kick off a Playwright scraper task in the background runner."""
    spawn_job(
        job_id=job_id,
        mode=payload.mode,
        prompt=payload.prompt,
        model_id=payload.model_id,
        settings=payload.settings.model_dump(),
        asset_ids=[ref.asset_id for ref in payload.references],
    )
