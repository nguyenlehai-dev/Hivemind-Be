"""session storage_state + error columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-21

"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.runway.orm import JsonColumn


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runway_sessions",
        sa.Column("storage_state", JsonColumn, nullable=True),
    )
    op.add_column(
        "runway_sessions",
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("runway_sessions", "error")
    op.drop_column("runway_sessions", "storage_state")
