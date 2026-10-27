from collections.abc import Iterator
from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from research_quest_api.database import Base, get_session
from research_quest_api.main import app
from research_quest_api.models import Document, DocumentStatus


def test_create_task_snapshots_selected_document() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    content = "Indexed content"
    document = Document(
        filename="notes.txt",
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        mime_type="text/plain",
        size_bytes=len(content),
        content=content,
        status=DocumentStatus.COMPLETED,
    )
    session.add(document)
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).post(
            "/api/tasks",
            json={
                "question": "  What does the document say?  ",
                "document_ids": [str(document.id)],
            },
        )
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()

    assert response.status_code == 201
    assert response.json()["question"] == "What does the document say?"
    assert response.json()["status"] == "queued"
    assert response.json()["document_ids"] == [str(document.id)]


def test_create_task_rejects_empty_question() -> None:
    response = TestClient(app).post(
        "/api/tasks",
        json={"question": "   "},
    )

    assert response.status_code == 422
