from collections.abc import Iterator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from research_quest_api.database import Base, get_session
from research_quest_api.main import app
from research_quest_api.models import TaskRecord


def create_test_client() -> tuple[TestClient, Session, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session, engine


def close_test_client(session: Session, engine: Engine) -> None:
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_get_task_returns_persisted_task() -> None:
    client, session, engine = create_test_client()
    task = TaskRecord(question="What changed?")
    session.add(task)
    session.commit()

    try:
        response = client.get(f"/api/tasks/{task.id}")
    finally:
        close_test_client(session, engine)

    assert response.status_code == 200
    assert response.json()["id"] == str(task.id)


def test_get_task_returns_not_found() -> None:
    client, session, engine = create_test_client()
    try:
        response = client.get(f"/api/tasks/{uuid4()}")
    finally:
        close_test_client(session, engine)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "task_not_found"


def test_list_tasks_applies_pagination() -> None:
    client, session, engine = create_test_client()
    session.add_all([TaskRecord(question=f"Question {index}") for index in range(3)])
    session.commit()

    try:
        response = client.get("/api/tasks?limit=2&offset=0")
    finally:
        close_test_client(session, engine)

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["has_more"] is True


def test_list_tasks_rejects_limit_above_maximum() -> None:
    response = TestClient(app).get("/api/tasks?limit=101")

    assert response.status_code == 422
