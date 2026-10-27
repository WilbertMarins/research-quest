from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from research_quest_api.database import get_session
from research_quest_api.tasks.repository import (
    DocumentSelectionError,
    TaskRepository,
)
from research_quest_api.tasks.schemas import CreateTaskRequest, TaskResponse

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
