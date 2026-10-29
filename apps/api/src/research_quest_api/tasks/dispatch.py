from typing import Protocol
from uuid import UUID

EXECUTE_TASK_NAME = "research_quest.execute_task"


class TaskDispatcher(Protocol):
    def dispatch(self, task_id: UUID) -> None: ...


class TaskPublisher(Protocol):
    def send_task(self, name: str, *, args: list[str]) -> object: ...


class CeleryTaskDispatcher:
    def __init__(self, app: TaskPublisher) -> None:
        self._app = app

    def dispatch(self, task_id: UUID) -> None:
        self._app.send_task(EXECUTE_TASK_NAME, args=[str(task_id)])


def get_task_dispatcher() -> TaskDispatcher:
    from research_quest_api.worker import celery_app

    return CeleryTaskDispatcher(celery_app)
