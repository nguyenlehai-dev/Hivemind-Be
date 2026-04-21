from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# JSONB on Postgres, JSON on others (SQLite in tests).
JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class SessionRow(Base):
    __tablename__ = "runway_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="connected")
    storage_state: Mapped[dict | None] = mapped_column(JsonColumn, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AssetRow(Base):
    __tablename__ = "runway_assets"

    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    preview_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AppRow(Base):
    """Saved preset of a composer state. Running an app creates a fresh
    generation using the preset's model/prompt/settings."""

    __tablename__ = "runway_apps"

    app_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    settings: Mapped[dict] = mapped_column(JsonColumn, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GenerationRow(Base):
    __tablename__ = "runway_generations"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result_urls: Mapped[list[str]] = mapped_column(
        JsonColumn, nullable=False, default=list
    )
    settings: Mapped[dict] = mapped_column(JsonColumn, nullable=False, default=dict)
    external_task_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
