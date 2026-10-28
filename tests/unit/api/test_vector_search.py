from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from research_quest_api.embeddings import DeterministicEmbeddingProvider
from research_quest_api.models import DocumentChunk
from research_quest_api.retrieval import VectorSearch


class StubSession:
    def __init__(self, rows: list[tuple[DocumentChunk, str, float]]) -> None:
        self.rows = rows
        self.executed = False

    def execute(self, statement: object) -> list[tuple[DocumentChunk, str, float]]:
        self.executed = True
        return self.rows


def test_vector_search_maps_ranked_chunks() -> None:
    document_id = uuid4()
    chunk = DocumentChunk(
        id=uuid4(),
        document_id=document_id,
        chunk_index=2,
        content="Trecho relevante",
        start_char=10,
        end_char=27,
    )
    session = StubSession([(chunk, "notes.md", 0.25)])
    search = VectorSearch(
        session=cast(Session, session),
        embedding_provider=DeterministicEmbeddingProvider(dimension=8),
    )

    result = search.search("pergunta", top_k=3, document_ids=(document_id,))

    assert session.executed is True
    assert result[0].chunk_id == chunk.id
    assert result[0].filename == "notes.md"
    assert result[0].score == pytest.approx(0.75)


def test_vector_search_skips_query_for_empty_document_snapshot() -> None:
    session = StubSession([])
    search = VectorSearch(
        session=cast(Session, session),
        embedding_provider=DeterministicEmbeddingProvider(dimension=8),
    )

    assert search.search("pergunta", top_k=3, document_ids=()) == ()
    assert session.executed is False


@pytest.mark.parametrize("top_k", [0, 51])
def test_vector_search_rejects_top_k_outside_limits(top_k: int) -> None:
    search = VectorSearch(
        session=cast(Session, StubSession([])),
        embedding_provider=DeterministicEmbeddingProvider(dimension=8),
    )

    with pytest.raises(ValueError, match="top_k"):
        search.search("pergunta", top_k=top_k)
