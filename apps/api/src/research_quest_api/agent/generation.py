from typing import Any, Protocol

from groq import Groq
from pydantic import SecretStr

from research_quest_api.agent.prompts import PromptMessage

ANSWER_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "source_chunk_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "insufficient_evidence": {"type": "boolean"},
    },
    "required": ["answer", "source_chunk_ids", "insufficient_evidence"],
    "additionalProperties": False,
}


class AnswerGenerator(Protocol):
    def generate(self, messages: tuple[PromptMessage, ...]) -> str: ...


class GroqAnswerGenerator:
    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        timeout_seconds: float = 30.0,
        max_completion_tokens: int = 2000,
        client: Any | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_completion_tokens <= 0:
            raise ValueError("max_completion_tokens must be greater than zero")
        self._model = model
        self._max_completion_tokens = max_completion_tokens
        self._client = client or Groq(
            api_key=api_key.get_secret_value(),
            timeout=timeout_seconds,
            max_retries=0,
        )

    def generate(self, messages: tuple[PromptMessage, ...]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            temperature=0,
            max_completion_tokens=self._max_completion_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "research_quest_answer",
                    "strict": True,
                    "schema": ANSWER_JSON_SCHEMA,
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise InvalidModelResponseError("The model returned empty content.")
        return content


class InvalidModelResponseError(ValueError):
    pass
