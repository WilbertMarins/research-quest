from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from research_quest_api.database import Base
from research_quest_api.tasks.domain import TaskStatus

task_status_type = Enum(
    TaskStatus,
    name="task_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda status: [item.value for item in status],
)
task_result_type = JSON().with_variant(JSONB(), "postgresql")


class TaskRecord(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_tasks_attempt_count_nonnegative",
        ),
        CheckConstraint("max_attempts > 0", name="ck_tasks_max_attempts_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        task_status_type,
        default=TaskStatus.QUEUED,
        server_default=TaskStatus.QUEUED.value,
        index=True,
    )
    result: Mapped[dict[str, object] | None] = mapped_column(task_result_type)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(64))

    documents: Mapped[list["TaskDocument"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskDocument.position",
    )

    @property
    def document_ids(self) -> tuple[UUID, ...]:
        return tuple(item.document_id for item in self.documents)


class TaskDocument(Base):
    __tablename__ = "task_documents"
    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="ck_task_documents_position_nonnegative",
        ),
        UniqueConstraint(
            "task_id",
            "position",
            name="uq_task_documents_task_position",
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    task: Mapped[TaskRecord] = relationship(back_populates="documents")
