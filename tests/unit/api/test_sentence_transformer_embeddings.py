from typing import Any

import pytest

from research_quest_api.embeddings import SentenceTransformerEmbeddingProvider


class EncodedVectors:
    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors

    def tolist(self) -> list[list[float]]:
        return self._vectors


class StubSentenceTransformer:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.received_texts: list[str] = []

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension

    def encode(self, texts: list[str], **kwargs: Any) -> EncodedVectors:
        self.received_texts = texts
        assert kwargs["normalize_embeddings"] is True
        return EncodedVectors([[0.5] * self.dimension for _ in texts])


def test_sentence_transformer_provider_loads_model_lazily() -> None:
    model = StubSentenceTransformer(dimension=3)
    loaded_models: list[str] = []

    def load_model(model_name: str) -> StubSentenceTransformer:
        loaded_models.append(model_name)
        return model

    provider = SentenceTransformerEmbeddingProvider(
        model_name="local-model",
        expected_dimension=3,
        model_factory=load_model,
    )

    assert loaded_models == []
    assert provider.embed_documents(["um", "dois"]) == [
        [0.5, 0.5, 0.5],
        [0.5, 0.5, 0.5],
    ]
    assert loaded_models == ["local-model"]
    assert model.received_texts == ["um", "dois"]


def test_sentence_transformer_provider_rejects_model_dimension_mismatch() -> None:
    provider = SentenceTransformerEmbeddingProvider(
        model_name="wrong-model",
        expected_dimension=384,
        model_factory=lambda _: StubSentenceTransformer(dimension=3),
    )

    with pytest.raises(ValueError, match="does not match"):
        provider.embed_documents(["content"])
