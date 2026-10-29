from collections.abc import Callable
from typing import Protocol
from uuid import UUID, uuid4

from celery import Celery
from sqlalchemy.orm import Session

from research_quest_api.agent import AgentResult, AgentTaskExecutor
from research_quest_api.agent.generation import GroqAnswerGenerator
from research_quest_api.database import SessionLocal
from research_quest_api.embeddings.dependencies import get_embedding_provider
from research_quest_api.retrieval import VectorSearch
from research_quest_api.settings import Settings, get_settings
from research_quest_api.tasks.dispatch import EXECUTE_TASK_NAME
from research_quest_api.tasks.repository import TaskRepository


class AgentExecutor(Protocol):
    def execute(self, task_id: UUID, *, trace_id: str) -> AgentResult: ...


def create_celery_app(settings: Settings | None = None) -> Celery:
    resolved_settings = settings or get_settings()
    app = Celery(
        "research_quest",
        broker=resolved_settings.celery_broker_url,
    )
    app.conf.update(
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
        enable_utc=True,
        result_backend=None,
        task_acks_late=True,
        task_default_queue="research_quest.tasks",
        task_reject_on_worker_lost=True,
        task_serializer="json",
        timezone="UTC",
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = create_celery_app()


def build_agent_executor(
    session: Session,
    settings: Settings | None = None,
) -> AgentTaskExecutor:
    resolved_settings = settings or get_settings()
    return AgentTaskExecutor(
        session=session,
        retriever=VectorSearch(
            session=session,
            embedding_provider=get_embedding_provider(),
        ),
        generator=GroqAnswerGenerator(
            api_key=resolved_settings.require_groq_api_key(),
            model=resolved_settings.groq_model,
        ),
        top_k=resolved_settings.retrieval_top_k,
    )


def run_agent_task(
    task_id: UUID,
    *,
    trace_id: str,
    session_factory: Callable[[], Session] = SessionLocal,
    executor_factory: Callable[[Session], AgentExecutor] = build_agent_executor,
) -> AgentResult:
    with session_factory() as session:
        return executor_factory(session).execute(task_id, trace_id=trace_id)


def record_task_failure(
    task_id: UUID,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    with session_factory() as session:
        TaskRepository(session).fail(
            task_id,
            error_code="agent_execution_failed",
            error_message="The research task could not be completed.",
        )
        session.commit()


@celery_app.task(bind=True, name=EXECUTE_TASK_NAME)
def execute_research_task(self: object, task_id: str) -> dict[str, object]:
    request = getattr(self, "request")
    trace_id = str(getattr(request, "id", None) or uuid4())
    parsed_task_id = UUID(task_id)
    try:
        result = run_agent_task(parsed_task_id, trace_id=trace_id)
    except Exception:
        record_task_failure(parsed_task_id)
        raise
    return result.model_dump(mode="json")
