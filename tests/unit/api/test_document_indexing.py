from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from research_quest_api.documents import DocumentIndexer, DocumentIndexingError
from research_quest_api.embeddings import DeterministicEmbeddingProvider
from research_quest_api.models import Document, DocumentStatus


def make_document(content: str = "abcdefgh") -> Document:
    return Document(
        filename="notes.txt",
        content_hash="a" * 64,
        mime_type="text/plain",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )


def make_indexer(
    session: Session,
    provider: DeterministicEmbeddingProvider,
) -> DocumentIndexer:
    return DocumentIndexer(
        session=session,
        embedding_provider=provider,
        chunk_size=5,
        chunk_overlap=1,
        max_chunks=10,
        expected_dimension=384,
    )


def test_document_indexer_persists_chunks_and_completes_document() -> None:
    session = Mock(spec=Session)
    provider = DeterministicEmbeddingProvider(dimension=384)
    document = make_document()

    chunks = make_indexer(session, provider).index(document)

    assert document.status is DocumentStatus.COMPLETED
    assert document.error_code is None
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert all(len(chunk.embedding or []) == 384 for chunk in chunks)
    assert all(chunk.embedding_provider == "fake" for chunk in chunks)
    session.add_all.assert_called_once_with(chunks)


class FailingEmbeddingProvider(DeterministicEmbeddingProvider):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider details must not leak")


def test_document_indexer_marks_provider_failure_without_leaking_details() -> None:
    session = Mock(spec=Session)
    document = make_document()
    indexer = make_indexer(session, FailingEmbeddingProvider(dimension=384))

    with pytest.raises(DocumentIndexingError) as captured:
        indexer.index(document)

    assert captured.value.code == "embedding_failed"
    assert "provider details" not in str(captured.value)
    assert document.status is DocumentStatus.FAILED
    assert document.error_code == "embedding_failed"
