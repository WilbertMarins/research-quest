from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from research_quest_api.models import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Stable identifier for the stored document.")
    filename: str = Field(description="Sanitized original filename.")
    mime_type: str = Field(description="Validated media type.")
    size_bytes: int = Field(description="Upload size before UTF-8 decoding.")
    status: DocumentStatus = Field(description="Current ingestion state.")
    error_code: str | None = Field(description="Safe failure code, when present.")
    chunk_count: int = Field(description="Number of persisted text chunks.")
    created: bool = Field(description="False when identical content already existed.")
    created_at: datetime


class ApiErrorDetail(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    detail: ApiErrorDetail
