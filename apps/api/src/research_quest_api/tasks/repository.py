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
from research_quest_api.tasks.domain import (
    ALLOWED_TRANSITIONS,
    InvalidTaskTransitionError,
    ResearchTask,
    TaskStatus,
    utc_now,
)


class DocumentSelectionError(ValueError):
    def __init__(self, document_ids: Sequence[UUID]) -> None:
        super().__init__("Selected documents must exist and be fully ingested.")
        self.document_ids = tuple(document_ids)


class TaskNotFoundError(LookupError):
    pass


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

    def start(self, task_id: UUID, *, trace_id: str) -> TaskRecord:
        if not trace_id or len(trace_id) > 64:
            raise ValueError("trace_id must contain between 1 and 64 characters")
        record = self._get_for_update(task_id)
        self._transition(record, TaskStatus.RUNNING)
        record.attempt_count += 1
        record.trace_id = trace_id
        record.error_code = None
        record.error_message = None
        self._session.flush()
        return record

    def complete(
        self,
        task_id: UUID,
        *,
        result: dict[str, object],
    ) -> TaskRecord:
        record = self._get_for_update(task_id)
        self._transition(record, TaskStatus.COMPLETED)
        record.result = result
        record.error_code = None
        record.error_message = None
        self._session.flush()
        return record

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

    def _get_for_update(self, task_id: UUID) -> TaskRecord:
        statement = select(TaskRecord).where(TaskRecord.id == task_id).with_for_update()
        record = self._session.scalar(statement)
        if record is None:
            raise TaskNotFoundError(f"Task {task_id} was not found.")
        return record

    @staticmethod
    def _transition(record: TaskRecord, target: TaskStatus) -> None:
        if target not in ALLOWED_TRANSITIONS[record.status]:
            raise InvalidTaskTransitionError(record.status, target)
        occurred_at = utc_now()
        record.status = target
        record.updated_at = occurred_at
        if target is TaskStatus.RUNNING and record.started_at is None:
            record.started_at = occurred_at
        if target in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
            record.finished_at = occurred_at
