from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_quest_api.tasks.domain import TaskStatus


class CreateTaskRequest(BaseModel):
    question: str = Field(description="Research question to answer from the snapshot.")
    document_ids: list[UUID] | None = Field(
        default=None,
        description=(
            "Completed documents to snapshot. Empty or omitted selects all completed "
            "documents available at creation time."
        ),
    )

    @field_validator("question")
    @classmethod
    def normalize_question(cls, question: str) -> str:
        normalized = question.strip()
        if not normalized:
            raise ValueError("Question cannot be empty.")
        return normalized


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    status: TaskStatus
    result: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    attempt_count: int
    max_attempts: int
    document_ids: tuple[UUID, ...]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class TaskListResponse(BaseModel):
    items: tuple[TaskResponse, ...]
    limit: int
    offset: int
    has_more: bool
