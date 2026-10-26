import pytest
from pydantic import ValidationError

from research_quest_api.settings import Settings


def test_settings_use_safe_mvp_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.embedding_dimension == 384
    assert settings.chunk_overlap < settings.chunk_size


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(_env_file=None, chunk_size=100, chunk_overlap=100)


def test_groq_key_is_required_only_when_generation_starts() -> None:
    settings = Settings(_env_file=None, groq_api_key=None)

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        settings.require_groq_api_key()
