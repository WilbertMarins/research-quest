from hashlib import sha256

import pytest
from sqlalchemy.orm import Session

from research_quest_api.database import create_database_engine
from research_quest_api.models import Document, DocumentStatus


@pytest.mark.integration
def test_document_can_be_persisted() -> None:
    content = "Pesquisa com conteúdo acentuado."
    engine = create_database_engine()

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        document = Document(
            filename="pesquisa.md",
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
            mime_type="text/markdown",
            size_bytes=len(content.encode("utf-8")),
            content=content,
        )

        session.add(document)
        session.flush()
        session.refresh(document)

        assert session.get(Document, document.id) is document
        assert document.status is DocumentStatus.PENDING
        assert document.created_at is not None
        assert document.updated_at is not None

        session.close()
        transaction.rollback()
