from uuid import uuid4

from research_quest_api.tasks.dispatch import (
    EXECUTE_TASK_NAME,
    CeleryTaskDispatcher,
)


class RecordingCeleryApp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def send_task(self, name: str, *, args: list[str]) -> None:
        self.calls.append((name, args))


def test_celery_dispatcher_publishes_only_the_task_identifier() -> None:
    app = RecordingCeleryApp()
    task_id = uuid4()

    CeleryTaskDispatcher(app).dispatch(task_id)

    assert app.calls == [(EXECUTE_TASK_NAME, [str(task_id)])]
