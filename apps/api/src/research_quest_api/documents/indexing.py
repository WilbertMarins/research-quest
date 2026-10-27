from sqlalchemy.orm import Session

from research_quest_api.documents.chunking import (
    ChunkLimitExceededError,
    split_text,
)
from research_quest_api.embeddings import EmbeddingProvider
from research_quest_api.models import Document, DocumentChunk, DocumentStatus


class DocumentIndexingError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DocumentIndexer:
    def __init__(
        self,
        *,
        session: Session,
        embedding_provider: EmbeddingProvider,
        chunk_size: int,
        chunk_overlap: int,
        max_chunks: int,
        expected_dimension: int,
    ) -> None:
        self._session = session
        self._embedding_provider = embedding_provider
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._max_chunks = max_chunks
        self._expected_dimension = expected_dimension

    def index(self, document: Document) -> tuple[DocumentChunk, ...]:
        document.status = DocumentStatus.PROCESSING
        document.error_code = None
        self._session.flush()

        try:
            chunks = split_text(
                document.content,
                chunk_size=self._chunk_size,
                overlap=self._chunk_overlap,
                max_chunks=self._max_chunks,
            )
            vectors = self._embedding_provider.embed_documents(
                [chunk.content for chunk in chunks]
            )
            self._validate_vectors(chunk_count=len(chunks), vectors=vectors)
        except ChunkLimitExceededError as error:
            self._mark_failed(document, "chunk_limit_exceeded")
            raise DocumentIndexingError(
                "chunk_limit_exceeded",
                "The document exceeds the configured chunk limit.",
            ) from error
        except Exception as error:
            self._mark_failed(document, "embedding_failed")
            raise DocumentIndexingError(
                "embedding_failed",
                "The document embedding could not be generated.",
            ) from error

        persisted_chunks = tuple(
            DocumentChunk(
                document=document,
                chunk_index=chunk.index,
                content=chunk.content,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                embedding=vector,
                embedding_provider=self._embedding_provider.provider_name,
                embedding_model=self._embedding_provider.model_name,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        )
        self._session.add_all(persisted_chunks)
        document.status = DocumentStatus.COMPLETED
        self._session.flush()
        return persisted_chunks

    def _validate_vectors(
        self,
        *,
        chunk_count: int,
        vectors: list[list[float]],
    ) -> None:
        if self._embedding_provider.dimension != self._expected_dimension:
            raise ValueError(
                "Embedding provider dimension is not configured correctly."
            )
        if len(vectors) != chunk_count:
            raise ValueError("Embedding provider returned an invalid batch size.")
        if any(len(vector) != self._expected_dimension for vector in vectors):
            raise ValueError("Embedding provider returned an invalid vector dimension.")

    def _mark_failed(self, document: Document, error_code: str) -> None:
        document.status = DocumentStatus.FAILED
        document.error_code = error_code
        self._session.flush()
