from uuid import uuid4

import pytest
from pydantic import ValidationError

from research_quest_api.agent import AgentResult, AgentRunInput, SourceReference


def test_agent_input_normalizes_question_and_preserves_snapshot() -> None:
    document_id = uuid4()
    run_input = AgentRunInput(
        task_id=uuid4(),
        question="  O que diz o documento?  ",
        document_ids=(document_id,),
    )

    assert run_input.question == "O que diz o documento?"
    assert run_input.document_ids == (document_id,)


def test_agent_input_rejects_empty_question() -> None:
    with pytest.raises(ValidationError, match="Question cannot be empty"):
        AgentRunInput(task_id=uuid4(), question="   ", document_ids=())


def test_grounded_result_requires_source() -> None:
    with pytest.raises(ValidationError, match="at least one source"):
        AgentResult(
            answer="Resposta sem fonte.",
            insufficient_evidence=False,
        )


def test_agent_result_accepts_retrieved_source() -> None:
    source = SourceReference(
        document_id=uuid4(),
        chunk_id=uuid4(),
        filename="notes.md",
        excerpt="Trecho que sustenta a resposta.",
    )

    result = AgentResult(
        answer="Resposta fundamentada.",
        sources=(source,),
        insufficient_evidence=False,
    )

    assert result.sources == (source,)


def test_insufficient_evidence_result_can_omit_sources() -> None:
    result = AgentResult(
        answer="Não há evidências suficientes nos documentos enviados.",
        insufficient_evidence=True,
    )

    assert result.sources == ()
