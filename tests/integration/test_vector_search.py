from hashlib import sha256

import pytest
from sqlalchemy.orm import Session

from research_quest_api.database import create_database_engine
from research_quest_api.embeddings import DeterministicEmbeddingProvider
from research_quest_api.models import Document, DocumentChunk, DocumentStatus
from research_quest_api.retrieval import VectorSearch


@pytest.mark.integration
def test_vector_search_filters_completed_selected_documents() -> None:
    provider = DeterministicEmbeddingProvider(dimension=384)
    engine = create_database_engine()

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        selected = _document_with_chunk(
            provider=provider,
            filename="selected.md",
            content="conteúdo selecionado",
            status=DocumentStatus.COMPLETED,
        )
        ignored = _document_with_chunk(
            provider=provider,
            filename="ignored.md",
            content="conteúdo ignorado",
            status=DocumentStatus.COMPLETED,
        )
        session.add_all([selected, ignored])
        session.flush()

        results = VectorSearch(
            session=session,
            embedding_provider=provider,
        ).search(
            "conteúdo selecionado",
            top_k=5,
            document_ids=(selected.id,),
        )

        assert len(results) == 1
        assert results[0].document_id == selected.id
        assert results[0].filename == "selected.md"

        session.close()
        transaction.rollback()


def _document_with_chunk(
    *,
    provider: DeterministicEmbeddingProvider,
    filename: str,
    content: str,
    status: DocumentStatus,
) -> Document:
    document = Document(
        filename=filename,
        content_hash=sha256(filename.encode("utf-8")).hexdigest(),
        mime_type="text/markdown",
        size_bytes=len(content.encode("utf-8")),
        content=content,
        status=status,
    )
    document.chunks.append(
        DocumentChunk(
            chunk_index=0,
            content=content,
            start_char=0,
            end_char=len(content),
            embedding=provider.embed_query(content),
            embedding_provider=provider.provider_name,
            embedding_model=provider.model_name,
        )
    )
    return document
