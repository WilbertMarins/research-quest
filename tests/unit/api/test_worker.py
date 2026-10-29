from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from research_quest_api.agent import AgentResult
from research_quest_api.settings import Settings
from research_quest_api.tasks.dispatch import EXECUTE_TASK_NAME
from research_quest_api.worker import celery_app, create_celery_app, run_agent_task


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
