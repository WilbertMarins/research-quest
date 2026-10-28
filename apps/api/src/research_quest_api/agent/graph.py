from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from research_quest_api.agent.contracts import AgentResult, AgentRunInput
from research_quest_api.agent.state import AgentState

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "Não há evidências suficientes nos documentos enviados para responder."
)


def validate_input(state: AgentState) -> AgentState:
    validated = AgentRunInput(
        task_id=state["task_id"],
        question=state["question"],
        document_ids=state["document_ids"],
    )
    return {
        "task_id": validated.task_id,
        "question": validated.question,
        "document_ids": validated.document_ids,
        "run_metadata": {"path": "deterministic_fake"},
    }


def finalize_without_evidence(state: AgentState) -> AgentState:
    return {
        **state,
        "sufficient_evidence": False,
        "result": AgentResult(
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            insufficient_evidence=True,
        ),
    }


def build_minimal_agent_graph() -> Any:
    builder = StateGraph(AgentState)
    builder.add_node("validate_input", validate_input)
    builder.add_node("finalize", finalize_without_evidence)
    builder.add_edge(START, "validate_input")
    builder.add_edge("validate_input", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


def run_minimal_agent(run_input: AgentRunInput) -> AgentResult:
    graph = build_minimal_agent_graph()
    final_state = graph.invoke(
        cast(AgentState, run_input.model_dump()),
        config={"recursion_limit": 8},
    )
    return cast(AgentResult, final_state["result"])
