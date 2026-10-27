from dataclasses import dataclass


class ChunkLimitExceededError(ValueError):
    def __init__(self, max_chunks: int) -> None:
        super().__init__(f"The document exceeds the limit of {max_chunks} chunks.")
        self.max_chunks = max_chunks


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int
    content: str
    start_char: int
    end_char: int


def split_text(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
    max_chunks: int,
) -> tuple[TextChunk, ...]:
    _validate_configuration(
        chunk_size=chunk_size,
        overlap=overlap,
        max_chunks=max_chunks,
    )

    if not text:
        return ()

    chunks: list[TextChunk] = []
    start = 0

    while start < len(text):
        if len(chunks) >= max_chunks:
            raise ChunkLimitExceededError(max_chunks)

        end = min(start + chunk_size, len(text))
        chunks.append(
            TextChunk(
                index=len(chunks),
                content=text[start:end],
                start_char=start,
                end_char=end,
            )
        )

        if end == len(text):
            break
        start = end - overlap

    return tuple(chunks)


def _validate_configuration(
    *,
    chunk_size: int,
    overlap: int,
    max_chunks: int,
) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if max_chunks <= 0:
        raise ValueError("max_chunks must be greater than zero")
