from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from research_quest_api.models import (
    Document,
    DocumentStatus,
    TaskDocument,
    TaskRecord,
)
from research_quest_api.tasks.domain import ResearchTask


class DocumentSelectionError(ValueError):
    def __init__(self, document_ids: Sequence[UUID]) -> None:
        super().__init__("Selected documents must exist and be fully ingested.")
        self.document_ids = tuple(document_ids)


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        question: str,
        document_ids: Sequence[UUID] | None,
    ) -> TaskRecord:
        domain_task = ResearchTask(question=question)
        resolved_document_ids = self._resolve_document_ids(document_ids)
        record = TaskRecord(
            id=domain_task.id,
            question=domain_task.question,
            status=domain_task.status,
            attempt_count=domain_task.attempt_count,
            max_attempts=domain_task.max_attempts,
            documents=[
                TaskDocument(document_id=document_id, position=position)
                for position, document_id in enumerate(resolved_document_ids)
            ],
        )
        self._session.add(record)
        self._session.flush()
        return record

    def get(self, task_id: UUID) -> TaskRecord | None:
        return self._session.get(TaskRecord, task_id)

    def list_recent(
        self,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[TaskRecord, ...]:
        statement = (
            select(TaskRecord)
            .order_by(TaskRecord.created_at.desc(), TaskRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return tuple(self._session.scalars(statement))

    def _resolve_document_ids(
        self,
        document_ids: Sequence[UUID] | None,
    ) -> tuple[UUID, ...]:
        requested = tuple(dict.fromkeys(document_ids or ()))
        statement = select(Document.id).where(
            Document.status == DocumentStatus.COMPLETED
        )

        if requested:
            available = set(
                self._session.scalars(statement.where(Document.id.in_(requested)))
            )
            missing = tuple(item for item in requested if item not in available)
            if missing:
                raise DocumentSelectionError(missing)
            return requested

        return tuple(
            self._session.scalars(statement.order_by(Document.created_at, Document.id))
        )
