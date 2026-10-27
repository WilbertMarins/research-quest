from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from research_quest_api.models import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    error_code: str | None
    chunk_count: int
    created: bool
    created_at: datetime
