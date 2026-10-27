from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from research_quest_api.documents.validation import ValidatedDocument
from research_quest_api.models import Document


@dataclass(frozen=True, slots=True)
class StoreDocumentResult:
    document: Document
    created: bool


class DocumentStorage:
    def __init__(self, session: Session) -> None:
        self._session = session

    def store(self, validated: ValidatedDocument) -> StoreDocumentResult:
        content_hash = calculate_content_hash(validated.content)
        existing = self._find_by_hash(content_hash)
        if existing is not None:
            return StoreDocumentResult(document=existing, created=False)

        document = Document(
            filename=validated.filename,
            content_hash=content_hash,
            mime_type=validated.mime_type,
            size_bytes=validated.size_bytes,
            content=validated.content,
        )

        try:
            with self._session.begin_nested():
                self._session.add(document)
                self._session.flush()
        except IntegrityError:
            existing = self._find_by_hash(content_hash)
            if existing is None:
                raise
            return StoreDocumentResult(document=existing, created=False)

        return StoreDocumentResult(document=document, created=True)

    def _find_by_hash(self, content_hash: str) -> Document | None:
        return self._session.scalar(
            select(Document).where(Document.content_hash == content_hash)
        )


def calculate_content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()
