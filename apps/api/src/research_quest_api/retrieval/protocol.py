from typing import Protocol
from uuid import UUID

from research_quest_api.retrieval.service import RetrievedChunk


class ChunkRetriever(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[RetrievedChunk, ...]: ...
