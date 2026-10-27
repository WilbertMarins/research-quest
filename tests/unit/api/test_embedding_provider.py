from math import sqrt

import pytest

from research_quest_api.embeddings import DeterministicEmbeddingProvider


def test_fake_embeddings_are_deterministic_and_have_expected_dimension() -> None:
    provider = DeterministicEmbeddingProvider(dimension=8)

    first, repeated = provider.embed_documents(["pesquisa", "pesquisa"])

    assert first == repeated
    assert len(first) == 8


def test_fake_embeddings_distinguish_text_and_are_normalized() -> None:
    provider = DeterministicEmbeddingProvider(dimension=16)

    first, second = provider.embed_documents(["primeiro", "segundo"])
    magnitude = sqrt(sum(value * value for value in first))

    assert first != second
    assert magnitude == pytest.approx(1.0)


def test_fake_embeddings_accept_an_empty_batch() -> None:
    provider = DeterministicEmbeddingProvider()

    assert provider.embed_documents([]) == []


def test_fake_embeddings_reject_invalid_dimension() -> None:
    with pytest.raises(ValueError, match="dimension"):
        DeterministicEmbeddingProvider(dimension=0)
