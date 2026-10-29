from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from random import uniform
from typing import Protocol
from uuid import UUID, uuid4

from celery import Celery
from groq import APIConnectionError, InternalServerError, RateLimitError
from sqlalchemy.orm import Session

from research_quest_api.agent import AgentResult, AgentTaskExecutor
from research_quest_api.agent.generation import GroqAnswerGenerator
from research_quest_api.database import SessionLocal
from research_quest_api.embeddings.dependencies import get_embedding_provider
from research_quest_api.retrieval import VectorSearch
from research_quest_api.settings import Settings, get_settings
from research_quest_api.tasks.dispatch import EXECUTE_TASK_NAME
from research_quest_api.tasks.repository import TaskRepository

TRANSIENT_PROVIDER_ERRORS = (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
)


class TaskExecutionFailedError(RuntimeError):
    pass


class TransientProviderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RetryDecision:
    should_retry: bool
    attempt_count: int
    max_attempts: int


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


def record_transient_failure(
    task_id: UUID,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> RetryDecision:
    with session_factory() as session:
        repository = TaskRepository(session)
        task = repository.mark_retrying(
            task_id,
            error_code="provider_temporarily_unavailable",
            error_message="The answer provider is temporarily unavailable.",
        )
        should_retry = task.attempt_count < task.max_attempts
        if not should_retry:
            repository.fail(
                task_id,
                error_code="retry_limit_exceeded",
                error_message="The research task exhausted its retry limit.",
            )
        decision = RetryDecision(
            should_retry=should_retry,
            attempt_count=task.attempt_count,
            max_attempts=task.max_attempts,
        )
        session.commit()
        return decision


def retry_after_seconds(error: Exception) -> int | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    raw_value = headers.get("retry-after") if headers is not None else None
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return max(1, ceil(value))


def calculate_retry_delay(
    attempt_count: int,
    *,
    retry_after: int | None = None,
    jitter: Callable[[float, float], float] = uniform,
) -> int:
    if retry_after is not None:
        return retry_after
    base_delay = min(2 ** max(attempt_count - 1, 0), 60)
    return ceil(base_delay + jitter(0, base_delay))


@celery_app.task(bind=True, name=EXECUTE_TASK_NAME)
def execute_research_task(self: object, task_id: str) -> dict[str, object]:
    request = getattr(self, "request")
    trace_id = str(getattr(request, "id", None) or uuid4())
    parsed_task_id = UUID(task_id)
    try:
        result = run_agent_task(parsed_task_id, trace_id=trace_id)
    except TRANSIENT_PROVIDER_ERRORS as error:
        decision = record_transient_failure(parsed_task_id)
        if decision.should_retry:
            countdown = calculate_retry_delay(
                decision.attempt_count,
                retry_after=retry_after_seconds(error),
            )
            retry = getattr(self, "retry")
            raise retry(
                exc=TransientProviderError(
                    "The answer provider is temporarily unavailable."
                ),
                countdown=countdown,
                max_retries=decision.max_attempts - 1,
            )
        raise TaskExecutionFailedError(
            "The research task exhausted its retry limit."
        ) from None
    except Exception:
        record_task_failure(parsed_task_id)
        raise TaskExecutionFailedError(
            "The research task could not be completed."
        ) from None
    return result.model_dump(mode="json")
