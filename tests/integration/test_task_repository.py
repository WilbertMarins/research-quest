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
