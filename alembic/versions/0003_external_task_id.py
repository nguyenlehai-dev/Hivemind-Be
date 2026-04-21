"""generation external_task_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-21

"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runway_generations",
        sa.Column("external_task_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_runway_generations_external_task_id",
        "runway_generations",
        ["external_task_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runway_generations_external_task_id",
        table_name="runway_generations",
    )
    op.drop_column("runway_generations", "external_task_id")
