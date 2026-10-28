from collections.abc import Callable
from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph

from research_quest_api.agent.contracts import (
    AgentResult,
    AgentRunInput,
    SourceReference,
)
from research_quest_api.agent.state import AgentState
from research_quest_api.retrieval import ChunkRetriever

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


def create_retrieve_context_node(
    retriever: ChunkRetriever,
    *,
    top_k: int,
) -> Callable[[AgentState], AgentState]:
    def retrieve_context(state: AgentState) -> AgentState:
        chunks = retriever.search(
            state["question"],
            top_k=top_k,
            document_ids=state["document_ids"],
        )
        return {**state, "retrieved_chunks": chunks}

    return retrieve_context


def create_assess_evidence_node(
    *,
    min_score: float,
) -> Callable[[AgentState], AgentState]:
    def assess_evidence(state: AgentState) -> AgentState:
        supported_chunks = tuple(
            chunk
            for chunk in state.get("retrieved_chunks", ())
            if chunk.score >= min_score
        )
        return {
            **state,
            "retrieved_chunks": supported_chunks,
            "sufficient_evidence": bool(supported_chunks),
        }

    return assess_evidence


def route_after_evidence(state: AgentState) -> Literal["grounded", "insufficient"]:
    if state.get("sufficient_evidence", False):
        return "grounded"
    return "insufficient"


def finalize_fake_grounded(state: AgentState) -> AgentState:
    chunks = state.get("retrieved_chunks", ())
    sources = tuple(
        SourceReference(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            filename=chunk.filename,
            excerpt=chunk.content[:500],
        )
        for chunk in chunks
    )
    return {
        **state,
        "result": AgentResult(
            answer="Evidências recuperadas; geração ainda não conectada.",
            sources=sources,
            insufficient_evidence=False,
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


def build_retrieval_agent_graph(
    retriever: ChunkRetriever,
    *,
    top_k: int = 5,
    min_score: float = 0.25,
) -> Any:
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if not -1.0 <= min_score <= 1.0:
        raise ValueError("min_score must be between -1 and 1")

    builder = StateGraph(AgentState)
    builder.add_node("validate_input", validate_input)
    builder.add_node(
        "retrieve_context",
        create_retrieve_context_node(retriever, top_k=top_k),
    )
    builder.add_node(
        "assess_evidence",
        create_assess_evidence_node(min_score=min_score),
    )
    builder.add_node("finalize_grounded", finalize_fake_grounded)
    builder.add_node("finalize_insufficient", finalize_without_evidence)
    builder.add_edge(START, "validate_input")
    builder.add_edge("validate_input", "retrieve_context")
    builder.add_edge("retrieve_context", "assess_evidence")
    builder.add_conditional_edges(
        "assess_evidence",
        route_after_evidence,
        {
            "grounded": "finalize_grounded",
            "insufficient": "finalize_insufficient",
        },
    )
    builder.add_edge("finalize_grounded", END)
    builder.add_edge("finalize_insufficient", END)
    return builder.compile()


def run_minimal_agent(run_input: AgentRunInput) -> AgentResult:
    graph = build_minimal_agent_graph()
    final_state = graph.invoke(
        cast(AgentState, run_input.model_dump()),
        config={"recursion_limit": 8},
    )
    return cast(AgentResult, final_state["result"])


def run_retrieval_agent(
    run_input: AgentRunInput,
    *,
    retriever: ChunkRetriever,
    top_k: int = 5,
    min_score: float = 0.25,
) -> AgentResult:
    graph = build_retrieval_agent_graph(
        retriever,
        top_k=top_k,
        min_score=min_score,
    )
    final_state = graph.invoke(
        cast(AgentState, run_input.model_dump()),
        config={"recursion_limit": 8},
    )
    return cast(AgentResult, final_state["result"])
