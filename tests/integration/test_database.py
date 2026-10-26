import pytest
from sqlalchemy import text

from research_quest_api.database import create_database_engine


@pytest.mark.integration
def test_pgvector_extension_is_available() -> None:
    engine = create_database_engine()

    with engine.connect() as connection:
        extension_version = connection.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )

    assert extension_version is not None
