from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import EntityNotFound
from app.core.ids import generate_id
from app.modules.runway.clients.runway_api import (
    RunwayAPIClient,
    RunwayAPIError,
    map_ratio,
)
from app.modules.runway.mock_image import build_mock_result_image
from app.modules.runway.orm import GenerationRow
from app.modules.runway.repositories import (
    AssetRepository,
    GenerationRepository,
    SessionRepository,
)
from app.modules.runway.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseData,
    GenerationDetailData,
    GenerationDetailResponse,
    GenerationListItem,
    GenerationListResponse,
)
from app.modules.runway.services.runway_scraper import RunwayScraperService
from app.modules.runway.services.scraper_runner import cancel_job, spawn_job


# Map Runway API task status → our status.
_STATUS_MAP = {
    "PENDING": "queued",
    "THROTTLED": "queued",
    "RUNNING": "running",
    "SUCCEEDED": "completed",
    "FAILED": "failed",
    "CANCELLED": "failed",
}


class GenerationService:
    def __init__(
        self,
        generations: GenerationRepository,
        assets: AssetRepository,
        sessions: SessionRepository,
        runway_api: RunwayAPIClient,
        scraper: RunwayScraperService,
    ) -> None:
        self._generations = generations
        self._assets = assets
        self._sessions = sessions
        self._runway_api = runway_api
        self._scraper = scraper

    async def create(self, payload: GenerateRequest) -> GenerateResponse:
        job_id = generate_id("job")
        backend = self._pick_backend(payload)

        task_id: str | None = None
        status = "queued"
        error: str | None = None
        result_urls: list[str] = []

        if backend == "api":
            task_id, status, error = await self._submit_api(payload)
        # scraper + mock: stay queued; scraper task spawned below, mock advances
        # via timer in _advance_mock on subsequent polls.

        row = GenerationRow(
            job_id=job_id,
            status=status,
            mode=payload.mode,
            model_id=payload.model_id,
            prompt=payload.prompt,
            result_urls=result_urls,
            settings=payload.settings.model_dump(),
            external_task_id=task_id,
            error=error,
        )
        await self._generations.add(row)

        if backend == "scraper" and status == "queued":
            # Spawn after DB insert so the runner can read the row via its own
            # session. create_task runs concurrently in the same event loop.
            spawn_job(
                job_id=job_id,
                mode=payload.mode,
                prompt=payload.prompt,
                model_id=payload.model_id,
                settings=payload.settings.model_dump(),
                asset_ids=[ref.asset_id for ref in payload.references],
            )

        return GenerateResponse(
            data=GenerateResponseData(job_id=job_id, status=status),
        )

    async def cancel(self, job_id: str) -> None:
        """Hybrid: cancel if in progress, delete row if terminal."""
        job = await self._generations.get(job_id)
        if job is None:
            raise EntityNotFound("Job not found", code="job_not_found")

        if job.status in ("completed", "failed"):
            await self._generations.delete(job_id)
            return

        cancelled = await cancel_job(job_id)

        if job.external_task_id and self._runway_api.is_configured:
            try:
                await self._runway_api.cancel_task(job.external_task_id)
            except Exception:
                pass

        job.status = "failed"
        job.error = "Cancelled by user" if cancelled else "Cancelled"

    async def retry(self, job_id: str) -> GenerateResponse:
        """Create a fresh generation with the same params as a terminal job.

        References aren't carried because asset_ids aren't stored on the job
        row — retries start clean; add references in the composer if needed.
        """
        job = await self._generations.get(job_id)
        if job is None:
            raise EntityNotFound("Job not found", code="job_not_found")

        if job.status not in ("completed", "failed"):
            from app.core.exceptions import BadRequest

            raise BadRequest(
                "Only terminal jobs can be retried", code="job_not_terminal"
            )

        from app.modules.runway.schemas import GenerationSettings

        payload = GenerateRequest(
            mode=job.mode,
            model_id=job.model_id,
            prompt=job.prompt,
            references=[],
            settings=(
                GenerationSettings(**job.settings)
                if job.settings
                else GenerationSettings()
            ),
        )
        return await self.create(payload)

    async def get(self, job_id: str) -> GenerationDetailResponse:
        job = await self._generations.get(job_id)
        if job is None:
            raise EntityNotFound("Job not found", code="job_not_found")

        await self._advance_status(job)

        return GenerationDetailResponse(
            data=GenerationDetailData(
                id=job.job_id,
                status=job.status,
                mode=job.mode,
                model_id=job.model_id,
                prompt=job.prompt,
                result_urls=job.result_urls,
                settings=job.settings,
                created_at=job.created_at.isoformat(),
                error=job.error,
            ),
        )

    async def list(self) -> GenerationListResponse:
        jobs = await self._generations.list()
        for job in jobs:
            await self._advance_status(job)

        items = [
            GenerationListItem(
                id=job.job_id,
                status=job.status,
                mode=job.mode,
                model_id=job.model_id,
                prompt=job.prompt,
                result_urls=job.result_urls,
                created_at=job.created_at.isoformat(),
            )
            for job in jobs
        ]
        return GenerationListResponse(data=items)

    # ------------------------------------------------------------------
    # Backend selection
    # ------------------------------------------------------------------

    def _pick_backend(self, payload: GenerateRequest) -> str:
        """Return one of: 'api', 'scraper', 'mock'."""
        configured = settings.runway_backend.lower()

        if configured == "api" and self._api_supports(payload):
            return "api"
        if configured == "scraper" and self._scraper_supports(payload):
            return "scraper"
        return "mock"

    def _api_supports(self, payload: GenerateRequest) -> bool:
        return (
            self._runway_api.is_configured
            and payload.mode == "video"
            and bool(payload.references)
        )

    def _scraper_supports(self, payload: GenerateRequest) -> bool:
        return payload.mode in ("image", "video", "audio")

    # ------------------------------------------------------------------
    # Submitters
    # ------------------------------------------------------------------

    async def _submit_api(
        self, payload: GenerateRequest
    ) -> tuple[str | None, str, str | None]:
        reference = payload.references[0]
        asset = await self._assets.get(reference.asset_id)
        if asset is None:
            return None, "failed", f"Reference {reference.asset_id} not found"

        try:
            response = await self._runway_api.image_to_video(
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


    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    async def _advance_status(self, job: GenerationRow) -> None:
        if job.status in ("completed", "failed"):
            return

        if job.external_task_id and self._runway_api.is_configured:
            await self._poll_runway(job)
            return

        self._advance_mock(job)

    async def _poll_runway(self, job: GenerationRow) -> None:
        try:
            task = await self._runway_api.get_task(job.external_task_id)
        except RunwayAPIError as exc:
            job.status = "failed"
            job.error = f"Runway poll failed: {exc.message}"
            return

        mapped = _STATUS_MAP.get(task.get("status", ""), job.status)
        job.status = mapped

        if mapped == "completed":
            output = task.get("output") or []
            job.result_urls = [
                item if isinstance(item, str) else item.get("url")
                for item in output
                if item
            ]
        elif mapped == "failed":
            job.error = task.get("failure") or task.get("failureCode") or "Runway task failed"

    def _advance_mock(self, job: GenerationRow) -> None:
        now = datetime.now(timezone.utc)
        created = job.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (now - created).total_seconds()
        if elapsed >= 3 and job.status != "completed":
            job.status = "completed"
            job.result_urls = [build_mock_result_image(job.prompt, job.model_id)]
        elif elapsed >= 1 and job.status == "queued":
            job.status = "running"
