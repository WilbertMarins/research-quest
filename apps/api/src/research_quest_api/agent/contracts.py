from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentRunInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    document_ids: tuple[UUID, ...]

    @field_validator("question")
    @classmethod
    def normalize_question(cls, question: str) -> str:
        normalized = question.strip()
        if not normalized:
            raise ValueError("Question cannot be empty.")
        return normalized


class SourceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    chunk_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(min_length=1, max_length=500)


class AgentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str = Field(min_length=1, max_length=12000)
    sources: tuple[SourceReference, ...] = ()
    insufficient_evidence: bool

    @model_validator(mode="after")
    def validate_sources(self) -> "AgentResult":
        if not self.insufficient_evidence and not self.sources:
            raise ValueError("A grounded answer must include at least one source.")
        return self
