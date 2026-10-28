from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from research_quest_api.agent.contracts import AgentResult, SourceReference
from research_quest_api.agent.generation import InvalidModelResponseError
from research_quest_api.retrieval import RetrievedChunk


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=12000)
    source_chunk_ids: tuple[UUID, ...]
    insufficient_evidence: bool

    @model_validator(mode="after")
    def validate_source_requirement(self) -> "GeneratedAnswer":
        if not self.insufficient_evidence and not self.source_chunk_ids:
            raise ValueError("A grounded answer must reference a source chunk.")
        if len(set(self.source_chunk_ids)) != len(self.source_chunk_ids):
            raise ValueError("Source chunk IDs must be unique.")
        return self


def validate_generated_answer(
    raw_answer: str,
    chunks: tuple[RetrievedChunk, ...],
) -> AgentResult:
    try:
        generated = GeneratedAnswer.model_validate_json(raw_answer)
    except ValidationError as error:
        raise InvalidModelResponseError(
            "The model response does not match the answer schema."
        ) from error

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    unknown_ids = set(generated.source_chunk_ids) - chunks_by_id.keys()
    if unknown_ids:
        raise InvalidModelResponseError(
            "The model referenced a chunk that was not retrieved."
        )

    sources = tuple(
        _source_from_chunk(chunks_by_id[chunk_id])
        for chunk_id in generated.source_chunk_ids
    )
    return AgentResult(
        answer=generated.answer,
        sources=sources,
        insufficient_evidence=generated.insufficient_evidence,
    )


def _source_from_chunk(chunk: RetrievedChunk) -> SourceReference:
    return SourceReference(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        filename=chunk.filename,
        excerpt=chunk.content[:500],
    )
