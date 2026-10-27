from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from research_quest_api.database import get_session
from research_quest_api.documents.indexing import (
    DocumentIndexer,
    DocumentIndexingError,
)
from research_quest_api.documents.schemas import ApiErrorResponse, DocumentResponse
from research_quest_api.documents.storage import DocumentStorage
from research_quest_api.documents.validation import (
    DocumentValidationError,
    validate_document,
)
from research_quest_api.embeddings.dependencies import get_embedding_provider
from research_quest_api.embeddings.provider import EmbeddingProvider
from research_quest_api.models import Document, DocumentChunk
from research_quest_api.settings import Settings, get_settings

router = APIRouter(prefix="/api/documents", tags=["documents"])

VALIDATION_STATUS_CODES = {
    "file_too_large": status.HTTP_413_CONTENT_TOO_LARGE,
    "unsupported_extension": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "unsupported_media_type": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a text document",
    description=(
        "Accepts UTF-8 TXT or Markdown, deduplicates by content, creates chunks "
        "and generates local embeddings. The original content is not returned."
    ),
    responses={
        200: {
            "model": DocumentResponse,
            "description": "Identical content already exists.",
        },
        413: {"model": ApiErrorResponse, "description": "Upload is too large."},
        415: {"model": ApiErrorResponse, "description": "Unsupported format."},
        422: {"model": ApiErrorResponse, "description": "Invalid text content."},
        503: {
            "model": ApiErrorResponse,
            "description": "Local embedding generation failed.",
        },
    },
)
async def upload_document(
    response: Response,
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentResponse:
    filename = file.filename
    mime_type = file.content_type
    try:
        content_bytes = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()

    try:
        validated = validate_document(
            filename=filename,
            mime_type=mime_type,
            content_bytes=content_bytes,
            max_bytes=settings.max_upload_bytes,
        )
    except DocumentValidationError as error:
        raise HTTPException(
            status_code=VALIDATION_STATUS_CODES.get(
                error.code,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
            detail={"code": error.code, "message": str(error)},
        ) from error

    stored = DocumentStorage(session).store(validated)
    if stored.created:
        indexer = DocumentIndexer(
            session=session,
            embedding_provider=embedding_provider,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            max_chunks=settings.max_chunks_per_document,
            expected_dimension=settings.embedding_dimension,
        )
        try:
            indexer.index(stored.document)
        except DocumentIndexingError as error:
            session.commit()
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                    if error.code == "chunk_limit_exceeded"
                    else status.HTTP_503_SERVICE_UNAVAILABLE
                ),
                detail={"code": error.code, "message": str(error)},
            ) from error
    else:
        response.status_code = status.HTTP_200_OK

    session.commit()
    session.refresh(stored.document)
    return _build_response(
        session=session,
        document=stored.document,
        created=stored.created,
    )


def _build_response(
    *,
    session: Session,
    document: Document,
    created: bool,
) -> DocumentResponse:
    chunk_count = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
    )
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=document.status,
        error_code=document.error_code,
        chunk_count=chunk_count or 0,
        created=created,
        created_at=document.created_at,
    )
