from functools import lru_cache

from research_quest_api.embeddings.provider import EmbeddingProvider
from research_quest_api.embeddings.sentence_transformers import (
    SentenceTransformerEmbeddingProvider,
)
from research_quest_api.settings import get_settings


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    return SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        expected_dimension=settings.embedding_dimension,
    )
