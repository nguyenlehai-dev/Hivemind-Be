"""Test the _sweep_stranded_jobs startup hook.

We exercise the function directly rather than simulating a full restart,
since the harness doesn't actually restart the app.
"""

import pytest
from sqlalchemy import select

from app.main import _sweep_stranded_jobs
from app.modules.runway.orm import GenerationRow


@pytest.mark.asyncio
async def test_sweep_marks_orphan_scraper_jobs_failed(
    client,  # noqa: ARG001 — forces DB override
    db_session_factory,
    monkeypatch,
):
    from app.core import database as db_mod

    # Point SessionLocal at the test engine so _sweep_stranded_jobs writes to
    # the same DB the test client reads from.
    monkeypatch.setattr(db_mod, "SessionLocal", db_session_factory)
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "SessionLocal", db_session_factory)

    # Seed one scraper (no external_task_id) + one API (with external_task_id).
    async with db_session_factory() as session:
        session.add_all([
            GenerationRow(
                job_id="scraper-stuck",
                status="running",
                mode="video",
                model_id="gen-4",
                prompt="stuck",
                result_urls=[],
                settings={},
                external_task_id=None,
            ),
            GenerationRow(
                job_id="api-alive",
                status="running",
                mode="video",
                model_id="gen-4",
                prompt="alive",
                result_urls=[],
                settings={},
                external_task_id="runway-xyz",
            ),
        ])
        await session.commit()

    await _sweep_stranded_jobs()

    async with db_session_factory() as session:
        scraper = (await session.execute(
            select(GenerationRow).where(GenerationRow.job_id == "scraper-stuck")
        )).scalar_one()
        api = (await session.execute(
            select(GenerationRow).where(GenerationRow.job_id == "api-alive")
        )).scalar_one()

    # Orphan scraper → failed
    assert scraper.status == "failed"
    assert "Stranded" in (scraper.error or "")

    # API job → still running (can be resumed)
    assert api.status == "running"
    assert api.error is None
