import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from research_quest_api.agent.generation import (
    ANSWER_JSON_SCHEMA,
    GroqAnswerGenerator,
    InvalidModelResponseError,
)
from research_quest_api.agent.prompts import PromptMessage
from research_quest_api.agent.validation import validate_generated_answer
from research_quest_api.retrieval import RetrievedChunk


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.received: dict[str, object] = {}

    def create(self, **kwargs: object) -> object:
        self.received = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename="manual.md",
        content="Trecho recuperado.",
        chunk_index=0,
        score=0.9,
    )


def test_groq_generator_requests_strict_structured_output() -> None:
    completions = FakeCompletions('{"answer":"ok"}')
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    )
    generator = GroqAnswerGenerator(
        api_key=SecretStr("secret"),
        model="openai/gpt-oss-20b",
        client=client,
    )

    result = generator.generate((PromptMessage(role="user", content="{}"),))

    response_format = completions.received["response_format"]
    assert result == '{"answer":"ok"}'
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"] == ANSWER_JSON_SCHEMA


def test_validator_maps_only_retrieved_source_ids() -> None:
    chunk = make_chunk()
    raw_answer = json.dumps(
        {
            "answer": "Resposta fundamentada.",
            "source_chunk_ids": [str(chunk.chunk_id)],
            "insufficient_evidence": False,
        }
    )

    result = validate_generated_answer(raw_answer, (chunk,))

    assert result.sources[0].chunk_id == chunk.chunk_id
    assert result.sources[0].excerpt == chunk.content


def test_validator_rejects_invented_source_id() -> None:
    raw_answer = json.dumps(
        {
            "answer": "Resposta com fonte inventada.",
            "source_chunk_ids": [str(uuid4())],
            "insufficient_evidence": False,
        }
    )

    with pytest.raises(InvalidModelResponseError, match="not retrieved"):
        validate_generated_answer(raw_answer, (make_chunk(),))


def test_validator_rejects_malformed_model_response() -> None:
    with pytest.raises(InvalidModelResponseError, match="schema"):
        validate_generated_answer("not-json", (make_chunk(),))
