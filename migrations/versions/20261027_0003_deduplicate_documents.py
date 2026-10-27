"""Make document content hashes unique.

Revision ID: 20261027_0003
Revises: 20261027_0002
Create Date: 2026-10-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261027_0003"
down_revision: str | None = "20261027_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_documents_content_hash"), table_name="documents")
    op.create_unique_constraint(
        "uq_documents_content_hash",
        "documents",
        ["content_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_documents_content_hash",
        "documents",
        type_="unique",
    )
    op.create_index(
        op.f("ix_documents_content_hash"),
        "documents",
        ["content_hash"],
        unique=False,
    )
