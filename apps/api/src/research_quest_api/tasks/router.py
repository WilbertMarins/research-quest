from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from research_quest_api.database import get_session
from research_quest_api.tasks.repository import (
    DocumentSelectionError,
    TaskRepository,
)
from research_quest_api.tasks.schemas import (
    CreateTaskRequest,
    TaskApiErrorResponse,
    TaskListResponse,
    TaskResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a research task",
    description=(
        "Creates a queued task and snapshots the selected completed documents. "
        "Agent execution is performed by a later workflow."
    ),
    responses={
        422: {
            "description": "Question or document selection is invalid.",
        }
    },
)
def create_task(
    request: CreateTaskRequest,
    session: Annotated[Session, Depends(get_session)],
) -> TaskResponse:
    try:
        task = TaskRepository(session).create(
            question=request.question,
            document_ids=request.document_ids,
        )
    except DocumentSelectionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_document_selection",
                "message": str(error),
            },
        ) from error

    session.commit()
    return TaskResponse.model_validate(task)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a research task",
    responses={
        404: {
            "description": "Task not found.",
            "model": TaskApiErrorResponse,
        }
    },
)
def get_task(
    task_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> TaskResponse:
    task = TaskRepository(session).get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": "Task not found."},
        )
    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List recent research tasks",
    description="Lists newest tasks first using limit and offset pagination.",
)
def list_tasks(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    records = TaskRepository(session).list_recent(
        limit=limit + 1,
        offset=offset,
    )
    return TaskListResponse(
        items=tuple(TaskResponse.model_validate(task) for task in records[:limit]),
        limit=limit,
        offset=offset,
        has_more=len(records) > limit,
    )
