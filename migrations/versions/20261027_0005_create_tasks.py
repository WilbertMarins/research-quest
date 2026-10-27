"""Create tasks and document snapshots.

Revision ID: 20261027_0005
Revises: 20261027_0004
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261027_0005"
down_revision: str | None = "20261027_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TASK_STATUSES = (
    "queued",
    "running",
    "waiting_for_tool",
    "retrying",
    "completed",
    "failed",
)


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *TASK_STATUSES,
                name="task_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_tasks_attempt_count_nonnegative",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="ck_tasks_max_attempts_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_created_at"), "tasks", ["created_at"])
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"])

    op.create_table(
        "task_documents",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "selected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_task_documents_position_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "document_id"),
        sa.UniqueConstraint(
            "task_id",
            "position",
            name="uq_task_documents_task_position",
        ),
    )
    op.create_index(
        op.f("ix_task_documents_document_id"),
        "task_documents",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_task_documents_document_id"),
        table_name="task_documents",
    )
    op.drop_table("task_documents")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_created_at"), table_name="tasks")
    op.drop_table("tasks")
