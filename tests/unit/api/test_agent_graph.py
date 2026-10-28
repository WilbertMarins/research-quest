from uuid import uuid4

from research_quest_api.agent import AgentRunInput, run_minimal_agent
from research_quest_api.agent.graph import INSUFFICIENT_EVIDENCE_MESSAGE


def test_minimal_graph_follows_deterministic_insufficient_evidence_path() -> None:
    run_input = AgentRunInput(
        task_id=uuid4(),
        question="O que está documentado?",
        document_ids=(),
    )

    result = run_minimal_agent(run_input)

    assert result.answer == INSUFFICIENT_EVIDENCE_MESSAGE
    assert result.insufficient_evidence is True
    assert result.sources == ()
