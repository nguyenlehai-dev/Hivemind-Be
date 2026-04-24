from app.core.config import settings
from app.core.exceptions import BadRequest, EntityNotFound
from app.core.ids import generate_id
from app.modules.runway.clients.runway_api import RunwayAPIClient
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
    GenerationSettings,
)
from app.modules.runway.services.generation.api_driver import (
    api_supports,
    poll_runway,
    submit_api,
)
from app.modules.runway.services.generation.mock_driver import advance_mock
from app.modules.runway.services.generation.scraper_driver import (
    scraper_supports,
    spawn_scraper_job,
)
from app.modules.runway.services.runway_scraper import RunwayScraperService
from app.modules.runway.services.scraper_runner import cancel_job


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

        if backend == "api":
            task_id, status, error = await submit_api(
                payload, self._runway_api, self._assets,
            )

        row = GenerationRow(
            job_id=job_id,
            status=status,
            mode=payload.mode,
            model_id=payload.model_id,
            prompt=payload.prompt,
            result_urls=[],
            settings=payload.settings.model_dump(),
            external_task_id=task_id,
            error=error,
        )
        await self._generations.add(row)

        if backend == "scraper" and status == "queued":
            spawn_scraper_job(job_id, payload)

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
        job = await self._generations.get(job_id)
        if job is None:
            raise EntityNotFound("Job not found", code="job_not_found")

        if job.status not in ("completed", "failed"):
            raise BadRequest(
                "Only terminal jobs can be retried", code="job_not_terminal",
            )

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

    def _pick_backend(self, payload: GenerateRequest) -> str:
        """Return one of: 'api', 'scraper', 'mock'."""
        configured = settings.runway_backend.lower()

        if configured == "api" and api_supports(payload, self._runway_api):
            return "api"
        if configured == "scraper" and scraper_supports(payload):
            return "scraper"
        return "mock"

    async def _advance_status(self, job: GenerationRow) -> None:
        if job.status in ("completed", "failed"):
            return

        if job.external_task_id and self._runway_api.is_configured:
            await poll_runway(job, self._runway_api)
            return

        advance_mock(job)
