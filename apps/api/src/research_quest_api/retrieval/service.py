from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from research_quest_api.embeddings import EmbeddingProvider
from research_quest_api.models import Document, DocumentChunk, DocumentStatus


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    chunk_index: int
    score: float


class VectorSearch:
    def __init__(
        self,
        *,
        session: Session,
        embedding_provider: EmbeddingProvider,
        max_top_k: int = 50,
    ) -> None:
        if max_top_k <= 0:
            raise ValueError("max_top_k must be greater than zero")
        self._session = session
        self._embedding_provider = embedding_provider
        self._max_top_k = max_top_k

    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")
        if not 1 <= top_k <= self._max_top_k:
            raise ValueError(f"top_k must be between 1 and {self._max_top_k}")
        if document_ids is not None and not document_ids:
            return ()

        query_vector = self._embedding_provider.embed_query(normalized_query)
        if len(query_vector) != self._embedding_provider.dimension:
            raise ValueError("query embedding has an invalid dimension")

        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        statement = (
            select(DocumentChunk, Document.filename, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.status == DocumentStatus.COMPLETED,
                DocumentChunk.embedding.is_not(None),
                DocumentChunk.embedding_provider
                == self._embedding_provider.provider_name,
                DocumentChunk.embedding_model == self._embedding_provider.model_name,
            )
            .order_by(distance, DocumentChunk.id)
            .limit(top_k)
        )
        if document_ids is not None:
            statement = statement.where(DocumentChunk.document_id.in_(document_ids))

        rows = self._session.execute(statement)
        return tuple(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                score=1.0 - float(raw_distance),
            )
            for chunk, filename, raw_distance in rows
        )
