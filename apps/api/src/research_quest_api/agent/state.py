from typing import NotRequired, TypedDict
from uuid import UUID

from research_quest_api.agent.contracts import AgentResult
from research_quest_api.retrieval import RetrievedChunk


class AgentState(TypedDict):
    task_id: UUID
    question: str
    document_ids: tuple[UUID, ...]
    retrieved_chunks: NotRequired[tuple[RetrievedChunk, ...]]
    sufficient_evidence: NotRequired[bool]
    result: NotRequired[AgentResult]
    error: NotRequired[str | None]
    run_metadata: NotRequired[dict[str, object]]
