from datetime import UTC, datetime

import pytest

from research_quest_api.tasks import (
    InvalidTaskTransitionError,
    ResearchTask,
    TaskStatus,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TaskStatus.QUEUED, TaskStatus.RUNNING),
        (TaskStatus.QUEUED, TaskStatus.FAILED),
        (TaskStatus.RUNNING, TaskStatus.WAITING_FOR_TOOL),
        (TaskStatus.RUNNING, TaskStatus.RETRYING),
        (TaskStatus.RUNNING, TaskStatus.COMPLETED),
        (TaskStatus.RUNNING, TaskStatus.FAILED),
        (TaskStatus.WAITING_FOR_TOOL, TaskStatus.RUNNING),
        (TaskStatus.RETRYING, TaskStatus.QUEUED),
        (TaskStatus.RETRYING, TaskStatus.RUNNING),
        (TaskStatus.RETRYING, TaskStatus.FAILED),
    ],
)
def test_task_accepts_defined_transitions(
    current: TaskStatus,
    target: TaskStatus,
) -> None:
    task = ResearchTask(question="Question", status=current)

    task.transition_to(target)

    assert task.status is target


def test_task_records_start_and_finish_times() -> None:
    started_at = datetime(2026, 10, 27, 12, tzinfo=UTC)
    finished_at = datetime(2026, 10, 27, 13, tzinfo=UTC)
    task = ResearchTask(question="  What is the subject?  ")

    task.transition_to(TaskStatus.RUNNING, occurred_at=started_at)
    task.transition_to(TaskStatus.COMPLETED, occurred_at=finished_at)

    assert task.question == "What is the subject?"
    assert task.started_at == started_at
    assert task.finished_at == finished_at
    assert task.updated_at == finished_at


@pytest.mark.parametrize("terminal", [TaskStatus.COMPLETED, TaskStatus.FAILED])
def test_task_rejects_transition_from_terminal_state(terminal: TaskStatus) -> None:
    task = ResearchTask(question="Question", status=terminal)

    with pytest.raises(InvalidTaskTransitionError) as captured:
        task.transition_to(TaskStatus.RUNNING)

    assert captured.value.current is terminal
    assert captured.value.target is TaskStatus.RUNNING


def test_task_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="question"):
        ResearchTask(question="   ")
