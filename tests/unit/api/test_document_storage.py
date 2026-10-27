from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from research_quest_api.database import Base
from research_quest_api.documents import (
    DocumentStorage,
    ValidatedDocument,
    calculate_content_hash,
)
from research_quest_api.models import Document


def make_validated_document(
    content: str,
    filename: str = "notes.txt",
) -> ValidatedDocument:
    return ValidatedDocument(
        filename=filename,
        mime_type="text/plain",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )


def test_document_storage_persists_content_hash() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        result = DocumentStorage(session).store(
            make_validated_document("Conteúdo persistido.")
        )

        assert result.created is True
        assert result.document.content_hash == calculate_content_hash(
            "Conteúdo persistido."
        )


def test_document_storage_returns_existing_document_for_duplicate_content() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        storage = DocumentStorage(session)
        first = storage.store(make_validated_document("Same content"))
        duplicate = storage.store(
            make_validated_document("Same content", filename="copy.md")
        )
        document_count = session.scalar(select(func.count()).select_from(Document))

        assert first.created is True
        assert duplicate.created is False
        assert duplicate.document.id == first.document.id
        assert duplicate.document.filename == "notes.txt"
        assert document_count == 1
