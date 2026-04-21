"""Background executor for scraper jobs.

- Jobs are spawned as asyncio tasks tracked in ``_active_tasks`` so they can be
  cancelled by ``job_id``.
- An ``asyncio.Lock`` serialises execution (shared browser context).
- Each task opens its own DB session (request session is already closed).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.database import SessionLocal
from app.modules.runway.repositories import (
    AssetRepository,
    GenerationRepository,
    SessionRepository,
)
from app.modules.runway.services.runway_scraper import (
    RunwayScraperError,
    RunwayScraperService,
)

_log = logging.getLogger("runway.scraper.runner")

# Only one scraper job at a time (shared browser context).
_scraper_lock = asyncio.Lock()

# job_id → asyncio.Task, so we can cancel.
_active_tasks: dict[str, asyncio.Task[Any]] = {}


def spawn_job(
    job_id: str,
    mode: str,
    prompt: str,
    model_id: str,
    settings: dict[str, Any],
    asset_ids: list[str],
) -> None:
    """Register a background scraper task for this job.

    Safe to call from inside an HTTP handler; the task runs concurrently.
    """
    if job_id in _active_tasks:
        _log.warning("scraper: job %s already has a task", job_id)
        return

    task = asyncio.create_task(
        _run(job_id, mode, prompt, model_id, settings, asset_ids),
        name=f"scraper-{job_id}",
    )
    _active_tasks[job_id] = task
    task.add_done_callback(lambda _t: _active_tasks.pop(job_id, None))


async def cancel_job(job_id: str) -> bool:
    """Cancel an in-flight scraper task. Returns True if we had a handle."""
    task = _active_tasks.get(job_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True


async def _run(
    job_id: str,
    mode: str,
    prompt: str,
    model_id: str,
    settings: dict[str, Any],
    asset_ids: list[str],
) -> None:
    """Driven by BackgroundTasks. Never raises; records errors in DB."""
    try:
        async with _scraper_lock:
            async with SessionLocal() as db:
                gen_repo = GenerationRepository(db)
                asset_repo = AssetRepository(db)
                session_repo = SessionRepository(db)

                job = await gen_repo.get(job_id)
                if job is None:
                    _log.error("scraper: job %s vanished before start", job_id)
                    return

                job.status = "running"
                await db.commit()

                try:
                    session = await session_repo.last()
                    if session is None or not session.storage_state:
                        raise RunwayScraperError(
                            "No Runway session available. "
                            "Click Connect Runway first.",
                        )

                    ref_urls: list[str] = []
                    for aid in asset_ids:
                        asset = await asset_repo.get(aid)
                        if asset is None:
                            raise RunwayScraperError(
                                f"Reference asset {aid} not found"
                            )
                        ref_urls.append(asset.preview_url)

                    scraper = RunwayScraperService()
                    result_url = await scraper.generate(
                        mode=mode,
                        prompt=prompt,
                        model_id=model_id,
                        settings=settings,
                        reference_data_urls=ref_urls,
                        storage_state=session.storage_state,
                    )

                    job = await gen_repo.get(job_id)
                    if job is None:
                        return
                    job.status = "completed"
                    job.result_urls = [result_url]
                    await db.commit()

                except asyncio.CancelledError:
                    await _mark_failed(db, gen_repo, job_id, "Cancelled by user")
                    raise
                except RunwayScraperError as exc:
                    await _mark_failed(db, gen_repo, job_id, exc.message)
                except Exception as exc:
                    _log.exception("scraper task crashed for %s", job_id)
                    await _mark_failed(db, gen_repo, job_id, f"Scraper crashed: {exc}")
    except asyncio.CancelledError:
        # Swallow to prevent unhandled exception noise; DB already updated above.
        pass


async def _mark_failed(
    db, repo: GenerationRepository, job_id: str, error: str
) -> None:
    try:
        job = await repo.get(job_id)
        if job is not None:
            job.status = "failed"
            job.error = error
            await db.commit()
    except Exception:
        _log.exception("failed to record failure for %s", job_id)
