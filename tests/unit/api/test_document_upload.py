from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from research_quest_api.database import Base, get_session
from research_quest_api.embeddings import DeterministicEmbeddingProvider
from research_quest_api.embeddings.dependencies import get_embedding_provider
from research_quest_api.main import app
from research_quest_api.settings import Settings, get_settings


def create_test_session() -> tuple[Session, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)

    return session, engine


def test_upload_document_indexes_content_without_returning_it() -> None:
    session, engine = create_test_session()
    settings = Settings(
        _env_file=None,
        embedding_dimension=384,
        chunk_size=10,
        chunk_overlap=2,
    )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedding_provider] = lambda: (
        DeterministicEmbeddingProvider(dimension=384)
    )

    try:
        response = TestClient(app).post(
            "/api/documents",
            files={
                "file": (
                    "pesquisa.md",
                    "Conteúdo de pesquisa com acentos.",
                    "text/markdown",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["created"] is True
    assert response.json()["chunk_count"] > 0
    assert "content" not in response.json()


def test_upload_document_returns_existing_document_for_duplicate() -> None:
    session, engine = create_test_session()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_embedding_provider] = lambda: (
        DeterministicEmbeddingProvider(dimension=384)
    )

    try:
        client = TestClient(app)
        first = client.post(
            "/api/documents",
            files={"file": ("first.txt", "same content", "text/plain")},
        )
        duplicate = client.post(
            "/api/documents",
            files={"file": ("copy.txt", "same content", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()

    assert first.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["created"] is False
    assert duplicate.json()["id"] == first.json()["id"]


def test_upload_document_rejects_unsupported_format() -> None:
    response = TestClient(app).post(
        "/api/documents",
        files={"file": ("notes.pdf", b"content", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_extension"
