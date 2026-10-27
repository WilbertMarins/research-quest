import pytest

from research_quest_api.documents import (
    DocumentValidationError,
    validate_document,
)


@pytest.mark.parametrize(
    ("filename", "mime_type"),
    [
        ("notes.txt", "text/plain"),
        ("notes.md", "text/markdown"),
        ("notes.MD", "text/plain"),
    ],
)
def test_validate_document_accepts_supported_text_files(
    filename: str,
    mime_type: str,
) -> None:
    content = "Informação com acentuação."

    validated = validate_document(
        filename=filename,
        mime_type=mime_type,
        content_bytes=content.encode("utf-8"),
        max_bytes=1024,
    )

    assert validated.filename == filename
    assert validated.content == content
    assert validated.size_bytes == len(content.encode("utf-8"))


def test_validate_document_keeps_only_the_filename() -> None:
    validated = validate_document(
        filename=r"C:\fakepath\notes.txt",
        mime_type="text/plain",
        content_bytes=b"Safe content",
        max_bytes=1024,
    )

    assert validated.filename == "notes.txt"


@pytest.mark.parametrize(
    ("filename", "mime_type", "content", "max_bytes", "expected_code"),
    [
        ("notes.pdf", "application/pdf", b"content", 1024, "unsupported_extension"),
        ("notes.txt", "application/json", b"content", 1024, "unsupported_media_type"),
        ("notes.txt", "text/plain", b"too large", 3, "file_too_large"),
        ("notes.txt", "text/plain", b" \n\t", 1024, "empty_document"),
        ("notes.txt", "text/plain", b"\xff", 1024, "invalid_encoding"),
    ],
)
def test_validate_document_rejects_invalid_input(
    filename: str,
    mime_type: str,
    content: bytes,
    max_bytes: int,
    expected_code: str,
) -> None:
    with pytest.raises(DocumentValidationError) as captured:
        validate_document(
            filename=filename,
            mime_type=mime_type,
            content_bytes=content,
            max_bytes=max_bytes,
        )

    assert captured.value.code == expected_code


def test_validate_document_accepts_utf8_bom() -> None:
    validated = validate_document(
        filename="notes.txt",
        mime_type="text/plain",
        content_bytes=b"\xef\xbb\xbfcontent",
        max_bytes=1024,
    )

    assert validated.content == "content"
