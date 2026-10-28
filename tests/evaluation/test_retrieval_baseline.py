import json
from pathlib import Path
from typing import TypedDict

import pytest

from research_quest_api.embeddings.dependencies import get_embedding_provider

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "retrieval_cases.json"
TOP_K = 2


class ChunkFixture(TypedDict):
    id: str
    content: str


class QueryFixture(TypedDict):
    query: str
    expected_chunk_id: str


class RetrievalFixture(TypedDict):
    chunks: list[ChunkFixture]
    cases: list[QueryFixture]


@pytest.mark.evaluation
def test_configured_embedding_model_retrieval_baseline() -> None:
    fixture = _load_fixture()
    provider = get_embedding_provider()
    chunks = fixture["chunks"]
    chunk_vectors = provider.embed_documents(
        [chunk["content"] for chunk in chunks]
    )

    misses: list[str] = []
    for case in fixture["cases"]:
        query_vector = provider.embed_query(case["query"])
        ranked_ids = _rank_chunk_ids(
            chunks=chunks,
            chunk_vectors=chunk_vectors,
            query_vector=query_vector,
        )
        if case["expected_chunk_id"] not in ranked_ids[:TOP_K]:
            misses.append(case["query"])

    assert not misses, f"Expected chunks were absent from top-{TOP_K}: {misses}"


def _load_fixture() -> RetrievalFixture:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _rank_chunk_ids(
    *,
    chunks: list[ChunkFixture],
    chunk_vectors: list[list[float]],
    query_vector: list[float],
) -> list[str]:
    scored = [
        (
            sum(left * right for left, right in zip(vector, query_vector, strict=True)),
            chunk["id"],
        )
        for chunk, vector in zip(chunks, chunk_vectors, strict=True)
    ]
    return [chunk_id for _, chunk_id in sorted(scored, reverse=True)]
