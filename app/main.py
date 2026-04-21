import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exception_handlers import register_exception_handlers
from app.modules.runway.orm import GenerationRow  # noqa: F401 register table
from app.modules.runway import orm as _orm  # noqa: F401 register all tables
from app.modules.runway.services.browser_manager import browser_manager

_log = logging.getLogger("hivemind.lifespan")


async def _sweep_stranded_jobs() -> None:
    """Recover jobs left non-terminal when the server crashed.

    Two classes of stranded jobs:
    - Scraper jobs (no external_task_id): the in-memory task handle is gone
      and there is no durable way to resume → mark failed.
    - Runway API jobs (external_task_id set): still running on Runway's side.
      Leave them as-is; the next _advance_status call will re-poll the API
      and pick up the result.
    """
    try:
        async with SessionLocal() as db:
            scraper_result = await db.execute(
                update(GenerationRow)
                .where(
                    GenerationRow.status.in_(["queued", "running"]),
                    GenerationRow.external_task_id.is_(None),
                )
                .values(
                    status="failed",
                    error="Stranded after server restart",
                )
            )
            await db.commit()
            if scraper_result.rowcount:
                _log.info(
                    "swept %d stranded scraper job(s)", scraper_result.rowcount
                )
    except Exception:
        _log.exception("stranded job sweep failed — continuing boot")


async def _ensure_schema() -> None:
    """For SQLite dev URLs, auto-create missing tables so the app boots without
    running alembic. Postgres prod should still use alembic migrations — we
    detect via dialect.
    """
    if "sqlite" not in settings.database_url:
        return
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _log.info("SQLite schema ensured via create_all")
    except Exception:
        _log.exception("SQLite schema setup failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _ensure_schema()
    await _sweep_stranded_jobs()
    yield
    # Graceful shutdown of the scraper's persistent browser (if started).
    await browser_manager.shutdown()


app = FastAPI(
    title="Hivemind BE",
    version="0.1.0",
    description="Runway custom workflow backend scaffold",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
