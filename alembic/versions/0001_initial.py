"""initial runway tables

Revision ID: 0001
Revises:
Create Date: 2026-04-21

"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.runway.orm import JsonColumn


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runway_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'connected'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "runway_assets",
        sa.Column("asset_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("preview_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "runway_generations",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column(
            "prompt",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "result_urls",
            JsonColumn,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "settings",
            JsonColumn,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_runway_generations_created_at",
        "runway_generations",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runway_generations_created_at", table_name="runway_generations"
    )
    op.drop_table("runway_generations")
    op.drop_table("runway_assets")
    op.drop_table("runway_sessions")
