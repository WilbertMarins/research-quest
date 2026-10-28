import json
from uuid import UUID, uuid4

import pytest

from research_quest_api.agent import AgentRunInput, run_grounded_agent
from research_quest_api.agent.prompts import PromptMessage
from research_quest_api.retrieval import RetrievedChunk


class FakeRetriever:
    def __init__(self, chunks: tuple[RetrievedChunk, ...]) -> None:
        self.chunks = chunks

    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        return self.chunks[:top_k]


class FailingRetriever:
    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        raise RetrievalUnavailableError("vector store unavailable")


class FakeGenerator:
    def __init__(self, content: str) -> None:
        self.content = content
        self.called = False

    def generate(self, messages: tuple[PromptMessage, ...]) -> str:
        self.called = True
        return self.content


class FailingGenerator:
    def generate(self, messages: tuple[PromptMessage, ...]) -> str:
        raise ModelUnavailableError("model unavailable")


class RetrievalUnavailableError(RuntimeError):
    pass


class ModelUnavailableError(RuntimeError):
    pass


def make_run_input(document_id: UUID) -> AgentRunInput:
    return AgentRunInput(
        task_id=uuid4(),
        question="O que informa o documento?",
        document_ids=(document_id,),
    )


def make_chunk(document_id: UUID, *, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=document_id,
        filename="manual.md",
        content="O documento informa uma evidência verificável.",
        chunk_index=0,
        score=score,
    )


def test_graph_completes_grounded_answer_with_real_source() -> None:
    document_id = uuid4()
    chunk = make_chunk(document_id)
    generator = FakeGenerator(
        json.dumps(
            {
                "answer": "Resposta sustentada pelo documento.",
                "source_chunk_ids": [str(chunk.chunk_id)],
                "insufficient_evidence": False,
            }
        )
    )

    result = run_grounded_agent(
        make_run_input(document_id),
        retriever=FakeRetriever((chunk,)),
        generator=generator,
    )

    assert result.answer == "Resposta sustentada pelo documento."
    assert result.sources[0].chunk_id == chunk.chunk_id
    assert generator.called is True


def test_graph_skips_model_when_evidence_is_insufficient() -> None:
    document_id = uuid4()
    generator = FakeGenerator("must not be used")

    result = run_grounded_agent(
        make_run_input(document_id),
        retriever=FakeRetriever(()),
        generator=generator,
    )

    assert result.insufficient_evidence is True
    assert result.sources == ()
    assert generator.called is False


def test_graph_propagates_model_failure() -> None:
    document_id = uuid4()

    with pytest.raises(ModelUnavailableError, match="model unavailable"):
        run_grounded_agent(
            make_run_input(document_id),
            retriever=FakeRetriever((make_chunk(document_id),)),
            generator=FailingGenerator(),
        )


def test_graph_propagates_retriever_failure_without_calling_model() -> None:
    document_id = uuid4()
    generator = FakeGenerator("must not be used")

    with pytest.raises(RetrievalUnavailableError, match="vector store unavailable"):
        run_grounded_agent(
            make_run_input(document_id),
            retriever=FailingRetriever(),
            generator=generator,
        )

    assert generator.called is False
