from collections.abc import Sequence
from hashlib import sha256
from math import sqrt


class DeterministicEmbeddingProvider:
    provider_name = "fake"
    model_name = "deterministic-sha256"

    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be greater than zero")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        values = [
            (digest[index % len(digest)] / 127.5) - 1.0
            for index in range(self.dimension)
        ]
        magnitude = sqrt(sum(value * value for value in values))
        return [value / magnitude for value in values]
