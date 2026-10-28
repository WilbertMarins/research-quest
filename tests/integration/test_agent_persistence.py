from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from research_quest_api.agent import AgentTaskExecutor
from research_quest_api.agent.prompts import PromptMessage
from research_quest_api.database import create_database_engine
from research_quest_api.models import TaskRecord
from research_quest_api.retrieval import RetrievedChunk
from research_quest_api.tasks import TaskStatus


class EmptyRetriever:
    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        return ()


class UnusedGenerator:
    def generate(self, messages: tuple[PromptMessage, ...]) -> str:
        raise AssertionError("Generator must not run without sufficient evidence.")


@pytest.mark.integration
def test_executor_persists_result_and_terminal_state() -> None:
    engine = create_database_engine()

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        task = TaskRecord(question="Pergunta sem documentos?")
        session.add(task)
        session.commit()

        result = AgentTaskExecutor(
            session=session,
            retriever=EmptyRetriever(),
            generator=UnusedGenerator(),
        ).execute(task.id, trace_id="test-trace")
        session.refresh(task)

        assert result.insufficient_evidence is True
        assert task.status is TaskStatus.COMPLETED
        assert task.result == result.model_dump(mode="json")
        assert task.attempt_count == 1
        assert task.trace_id == "test-trace"
        assert task.started_at is not None
        assert task.finished_at is not None

        session.close()
        transaction.rollback()
