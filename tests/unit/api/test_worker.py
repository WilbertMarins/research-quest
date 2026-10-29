from uuid import UUID, uuid4

import httpx
from groq import APIConnectionError, RateLimitError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from research_quest_api.agent import AgentResult
from research_quest_api.database import Base
from research_quest_api.models import TaskRecord
from research_quest_api.settings import Settings
from research_quest_api.tasks import TaskStatus
from research_quest_api.tasks.dispatch import EXECUTE_TASK_NAME
from research_quest_api.tasks.repository import TaskRepository
from research_quest_api.worker import (
    TRANSIENT_PROVIDER_ERRORS,
    calculate_retry_delay,
    celery_app,
    create_celery_app,
    record_transient_failure,
    retry_after_seconds,
    run_agent_task,
)


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    def execute(self, task_id: UUID, *, trace_id: str) -> AgentResult:
        self.calls.append((task_id, trace_id))
        return AgentResult(
            answer="Evidence was insufficient.",
            insufficient_evidence=True,
        )


def test_celery_app_uses_rabbitmq_and_safe_serializers() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://test:test@localhost/test",
        celery_broker_url="amqp://worker:secret@rabbitmq:5672//",
    )

    app = create_celery_app(settings)

    assert app.conf.broker_url == settings.celery_broker_url
    assert app.conf.task_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert app.conf.result_backend is None
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1


def test_worker_registers_research_task() -> None:
    assert EXECUTE_TASK_NAME in celery_app.tasks


def test_run_agent_task_executes_with_task_and_trace_identifiers() -> None:
    executor = RecordingExecutor()
    task_id = uuid4()

    result = run_agent_task(
        task_id,
        trace_id="celery-message-id",
        session_factory=Session,
        executor_factory=lambda session: executor,
    )

    assert result.insufficient_evidence is True
    assert executor.calls == [(task_id, "celery-message-id")]


def test_retry_delay_uses_exponential_backoff_and_jitter() -> None:
    delay = calculate_retry_delay(
        2,
        jitter=lambda start, end: 0.5,
    )

    assert delay == 3
    assert calculate_retry_delay(2, retry_after=7) == 7


def test_retry_after_is_read_from_rate_limit_response() -> None:
    request = httpx.Request(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions",
    )
    response = httpx.Response(429, request=request, headers={"retry-after": "2.2"})
    error = RateLimitError("Rate limited", response=response, body=None)

    assert retry_after_seconds(error) == 3


def test_only_provider_transport_and_temporary_status_errors_are_retryable() -> None:
    request = httpx.Request(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions",
    )

    assert isinstance(APIConnectionError(request=request), TRANSIENT_PROVIDER_ERRORS)
    assert not isinstance(ValueError("invalid model response"), TRANSIENT_PROVIDER_ERRORS)


def test_transient_failure_stops_retrying_at_task_limit() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        task = TaskRecord(
            question="Will the provider recover?",
            status=TaskStatus.RUNNING,
            attempt_count=1,
            max_attempts=2,
        )
        session.add(task)
        session.commit()
        task_id = task.id

    first_decision = record_transient_failure(
        task_id,
        session_factory=session_factory,
    )
    with session_factory() as session:
        TaskRepository(session).start(task_id, trace_id="second-attempt")
        session.commit()

    final_decision = record_transient_failure(
        task_id,
        session_factory=session_factory,
    )
    with session_factory() as session:
        persisted_task = session.get(TaskRecord, task_id)

    assert first_decision.should_retry is True
    assert final_decision.should_retry is False
    assert persisted_task is not None
    assert persisted_task.status is TaskStatus.FAILED
    assert persisted_task.error_code == "retry_limit_exceeded"
    engine.dispose()
