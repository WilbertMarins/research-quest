from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = (
        "postgresql+psycopg://research_quest:research_quest@localhost:5432/"
        "research_quest"
    )

    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-20b"

    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    embedding_dimension: int = Field(default=384, gt=0)

    max_upload_bytes: int = Field(default=2 * 1024 * 1024, gt=0)
    max_chunks_per_document: int = Field(default=2000, gt=0)
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)
    retrieval_top_k: int = Field(default=5, gt=0, le=50)

    @model_validator(mode="after")
    def validate_chunk_window(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    def require_groq_api_key(self) -> SecretStr:
        if self.groq_api_key is None or not self.groq_api_key.get_secret_value():
            raise ValueError("GROQ_API_KEY is required for answer generation")
        return self.groq_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
