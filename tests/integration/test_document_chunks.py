from hashlib import sha256

import pytest
from sqlalchemy.orm import Session

from research_quest_api.database import create_database_engine
from research_quest_api.models import Document, DocumentChunk


@pytest.mark.integration
def test_document_chunk_can_persist_a_vector() -> None:
    content = "A chunk with a local embedding."
    engine = create_database_engine()

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        document = Document(
            filename="vector.txt",
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
            mime_type="text/plain",
            size_bytes=len(content.encode("utf-8")),
            content=content,
        )
        chunk = DocumentChunk(
            document=document,
            chunk_index=0,
            content=content,
            start_char=0,
            end_char=len(content),
            embedding=[0.0] * 384,
            embedding_provider="sentence-transformers",
            embedding_model=(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            ),
        )

        session.add(chunk)
        session.flush()
        session.refresh(chunk)

        assert chunk.document_id == document.id
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 384

        session.close()
        transaction.rollback()
