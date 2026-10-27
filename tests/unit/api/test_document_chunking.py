import pytest

from research_quest_api.documents import ChunkLimitExceededError, split_text


def test_split_text_preserves_order_offsets_and_overlap() -> None:
    text = "abcdefghijklmnop"

    chunks = split_text(
        text,
        chunk_size=6,
        overlap=2,
        max_chunks=10,
    )

    assert [chunk.index for chunk in chunks] == [0, 1, 2, 3]
    assert [chunk.content for chunk in chunks] == [
        "abcdef",
        "efghij",
        "ijklmn",
        "mnop",
    ]
    assert [(chunk.start_char, chunk.end_char) for chunk in chunks] == [
        (0, 6),
        (4, 10),
        (8, 14),
        (12, 16),
    ]


def test_split_text_preserves_unicode_characters() -> None:
    text = "ação🙂pesquisa"

    chunks = split_text(
        text,
        chunk_size=5,
        overlap=1,
        max_chunks=10,
    )

    reconstructed = chunks[0].content + "".join(
        chunk.content[1:] for chunk in chunks[1:]
    )
    assert reconstructed == text
    assert all(
        chunk.content == text[chunk.start_char : chunk.end_char] for chunk in chunks
    )


def test_split_text_returns_no_chunks_for_empty_text() -> None:
    assert split_text("", chunk_size=10, overlap=2, max_chunks=10) == ()


def test_split_text_rejects_documents_above_chunk_limit() -> None:
    with pytest.raises(ChunkLimitExceededError) as captured:
        split_text(
            "123456789",
            chunk_size=4,
            overlap=1,
            max_chunks=2,
        )

    assert captured.value.max_chunks == 2


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "max_chunks"),
    [
        (0, 0, 1),
        (10, -1, 1),
        (10, 10, 1),
        (10, 0, 0),
    ],
)
def test_split_text_rejects_invalid_configuration(
    chunk_size: int,
    overlap: int,
    max_chunks: int,
) -> None:
    with pytest.raises(ValueError):
        split_text(
            "content",
            chunk_size=chunk_size,
            overlap=overlap,
            max_chunks=max_chunks,
        )
