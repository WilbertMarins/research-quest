from dataclasses import dataclass
from pathlib import PurePath

SUPPORTED_MEDIA_TYPES = {
    ".md": frozenset({"text/markdown", "text/plain"}),
    ".txt": frozenset({"text/plain"}),
}


class DocumentValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ValidatedDocument:
    filename: str
    mime_type: str
    size_bytes: int
    content: str


def validate_document(
    *,
    filename: str | None,
    mime_type: str | None,
    content_bytes: bytes,
    max_bytes: int,
) -> ValidatedDocument:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")

    safe_filename = _extract_filename(filename)
    extension = PurePath(safe_filename).suffix.lower()
    allowed_media_types = SUPPORTED_MEDIA_TYPES.get(extension)

    if allowed_media_types is None:
        raise DocumentValidationError(
            "unsupported_extension",
            "Only .txt and .md files are supported.",
        )

    normalized_mime_type = (mime_type or "").partition(";")[0].strip().lower()
    if normalized_mime_type not in allowed_media_types:
        raise DocumentValidationError(
            "unsupported_media_type",
            "The file media type does not match a supported text format.",
        )

    size_bytes = len(content_bytes)
    if size_bytes > max_bytes:
        raise DocumentValidationError(
            "file_too_large",
            f"The file exceeds the configured limit of {max_bytes} bytes.",
        )

    try:
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentValidationError(
            "invalid_encoding",
            "The file must use UTF-8 encoding.",
        ) from error

    if not content.strip():
        raise DocumentValidationError(
            "empty_document",
            "The file must contain non-whitespace text.",
        )

    return ValidatedDocument(
        filename=safe_filename,
        mime_type=normalized_mime_type,
        size_bytes=size_bytes,
        content=content,
    )


def _extract_filename(filename: str | None) -> str:
    safe_filename = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not safe_filename or safe_filename in {".", ".."}:
        raise DocumentValidationError(
            "invalid_filename",
            "The file must have a valid name.",
        )
    return safe_filename
