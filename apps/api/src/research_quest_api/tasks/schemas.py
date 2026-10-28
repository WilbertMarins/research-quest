from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_quest_api.tasks.domain import TaskStatus


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "Quais são os principais pontos dos documentos?",
                    "document_ids": [],
                }
            ]
        }
    )

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

    id: UUID = Field(description="Stable identifier for the research task.")
    question: str = Field(description="Normalized research question.")
    status: TaskStatus = Field(description="Current execution state.")
    result: dict[str, object] | None = Field(
        description="Grounded answer payload when execution completes."
    )
    error_code: str | None = Field(description="Safe failure code, when present.")
    error_message: str | None = Field(
        description="Safe failure explanation without internal details."
    )
    attempt_count: int = Field(description="Number of execution attempts.")
    max_attempts: int = Field(description="Maximum execution attempts allowed.")
    document_ids: tuple[UUID, ...] = Field(
        description="Immutable document selection captured at creation time."
    )
    created_at: datetime = Field(description="UTC creation timestamp.")
    updated_at: datetime = Field(description="UTC last-update timestamp.")
    started_at: datetime | None = Field(description="UTC execution start timestamp.")
    finished_at: datetime | None = Field(
        description="UTC terminal-state timestamp."
    )


class TaskListResponse(BaseModel):
    items: tuple[TaskResponse, ...] = Field(description="Tasks ordered newest first.")
    limit: int = Field(description="Maximum number of returned tasks.")
    offset: int = Field(description="Number of newer tasks skipped.")
    has_more: bool = Field(description="Whether another page is available.")


class TaskApiErrorDetail(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Safe human-readable error message.")


class TaskApiErrorResponse(BaseModel):
    detail: TaskApiErrorDetail
