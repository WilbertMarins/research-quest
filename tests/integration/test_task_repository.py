from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from research_quest_api.database import create_database_engine
from research_quest_api.models import Document, DocumentStatus
from research_quest_api.tasks import TaskStatus
from research_quest_api.tasks.repository import DocumentSelectionError, TaskRepository


def make_document(status: DocumentStatus) -> Document:
    content = f"document-{uuid4()}"
    return Document(
        filename="document.txt",
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
        mime_type="text/plain",
        size_bytes=len(content),
        content=content,
        status=status,
    )


@pytest.mark.integration
def test_task_repository_snapshots_only_completed_documents() -> None:
    engine = create_database_engine()

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        completed = make_document(DocumentStatus.COMPLETED)
        pending = make_document(DocumentStatus.PENDING)
        session.add_all([completed, pending])
        session.flush()

        task = TaskRepository(session).create(
            question="  What is in the documents?  ",
            document_ids=None,
        )

        assert task.status is TaskStatus.QUEUED
        assert task.question == "What is in the documents?"
        assert task.document_ids == (completed.id,)

        with pytest.raises(DocumentSelectionError):
            TaskRepository(session).create(
                question="Invalid selection",
                document_ids=[pending.id],
            )

        session.close()
        transaction.rollback()


@pytest.mark.integration
def test_task_repository_persists_retry_and_failure_states() -> None:
    engine = create_database_engine()

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        repository = TaskRepository(session)
        task = repository.create(question="Will this retry?", document_ids=None)

        repository.start(task.id, trace_id="first-attempt")
        repository.mark_retrying(
            task.id,
            error_code="provider_unavailable",
            error_message="The answer provider is temporarily unavailable.",
        )

        assert task.status is TaskStatus.RETRYING
        assert task.attempt_count == 1
        assert task.finished_at is None

        repository.start(task.id, trace_id="second-attempt")
        repository.fail(
            task.id,
            error_code="agent_execution_failed",
            error_message="The research task could not be completed.",
        )

        assert task.status is TaskStatus.FAILED
        assert task.attempt_count == 2
        assert task.finished_at is not None
        assert task.error_code == "agent_execution_failed"

        session.close()
        transaction.rollback()
