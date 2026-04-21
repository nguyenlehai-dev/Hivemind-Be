"""runway_apps table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-21

"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.runway.orm import JsonColumn


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runway_apps",
        sa.Column("app_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "description", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "settings",
            JsonColumn,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_runway_apps_created_at", "runway_apps", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_runway_apps_created_at", table_name="runway_apps")
    op.drop_table("runway_apps")
