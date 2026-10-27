from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_TOOL = "waiting_for_tool"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


ALLOWED_TRANSITIONS = {
    TaskStatus.QUEUED: frozenset({TaskStatus.RUNNING, TaskStatus.FAILED}),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.WAITING_FOR_TOOL,
            TaskStatus.RETRYING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        }
    ),
    TaskStatus.WAITING_FOR_TOOL: frozenset({TaskStatus.RUNNING}),
    TaskStatus.RETRYING: frozenset(
        {TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.FAILED}
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset(),
}


class InvalidTaskTransitionError(ValueError):
    def __init__(self, current: TaskStatus, target: TaskStatus) -> None:
        super().__init__(f"Task cannot transition from {current} to {target}.")
        self.current = current
        self.target = target


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ResearchTask:
    question: str
    id: UUID = field(default_factory=uuid4)
    status: TaskStatus = TaskStatus.QUEUED
    result: dict[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trace_id: str | None = None
    document_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("Task question cannot be empty.")
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero")

    def transition_to(
        self,
        target: TaskStatus,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        if target not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidTaskTransitionError(self.status, target)

        transition_time = occurred_at or utc_now()
        self.status = target
        self.updated_at = transition_time

        if target is TaskStatus.RUNNING and self.started_at is None:
            self.started_at = transition_time
        if target in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
            self.finished_at = transition_time
