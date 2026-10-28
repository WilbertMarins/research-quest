from collections.abc import Callable, Sequence
from typing import Any, Protocol


class _SentenceTransformerModel(Protocol):
    def get_sentence_embedding_dimension(self) -> int | None: ...

    def encode(self, texts: list[str], **kwargs: Any) -> Any: ...


class SentenceTransformerEmbeddingProvider:
    provider_name = "sentence-transformers"

    def __init__(
        self,
        *,
        model_name: str,
        expected_dimension: int,
        model_factory: Callable[[str], _SentenceTransformerModel] | None = None,
    ) -> None:
        if expected_dimension <= 0:
            raise ValueError("expected_dimension must be greater than zero")
        self.model_name = model_name
        self._dimension = expected_dimension
        self._model_factory = model_factory or _load_sentence_transformer
        self._model: _SentenceTransformerModel | None = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._get_model()
        encoded = model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        vectors = encoded.tolist()

        if len(vectors) != len(texts):
            raise ValueError("The embedding provider returned an invalid batch size.")
        if any(len(vector) != self.dimension for vector in vectors):
            raise ValueError("The embedding provider returned an invalid dimension.")

        return vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_documents([text])
        return vectors[0]

    def _get_model(self) -> _SentenceTransformerModel:
        if self._model is None:
            model = self._model_factory(self.model_name)
            actual_dimension = model.get_sentence_embedding_dimension()
            if actual_dimension != self.dimension:
                raise ValueError(
                    "The configured embedding dimension does not match the model."
                )
            self._model = model
        return self._model


def _load_sentence_transformer(model_name: str) -> _SentenceTransformerModel:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, trust_remote_code=False)
