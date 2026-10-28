from uuid import UUID, uuid4

from research_quest_api.agent import AgentRunInput, run_retrieval_agent
from research_quest_api.retrieval import RetrievedChunk


class FakeRetriever:
    def __init__(self, chunks: tuple[RetrievedChunk, ...]) -> None:
        self.chunks = chunks
        self.received_query: str | None = None
        self.received_document_ids: tuple[UUID, ...] | None = None

    def search(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        self.received_query = query
        self.received_document_ids = document_ids
        return self.chunks[:top_k]


def test_retrieval_graph_returns_sources_from_task_snapshot() -> None:
    document_id = uuid4()
    chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=document_id,
        filename="manual.md",
        content="Evidência recuperada do manual.",
        chunk_index=0,
        score=0.8,
    )
    retriever = FakeRetriever((chunk,))
    run_input = AgentRunInput(
        task_id=uuid4(),
        question="O que diz o manual?",
        document_ids=(document_id,),
    )

    result = run_retrieval_agent(run_input, retriever=retriever, min_score=0.5)

    assert retriever.received_query == run_input.question
    assert retriever.received_document_ids == (document_id,)
    assert result.insufficient_evidence is False
    assert result.sources[0].chunk_id == chunk.chunk_id


def test_retrieval_graph_reports_insufficient_low_score_evidence() -> None:
    chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename="unrelated.md",
        content="Conteúdo sem relação suficiente.",
        chunk_index=0,
        score=0.1,
    )
    run_input = AgentRunInput(
        task_id=uuid4(),
        question="Pergunta sem resposta?",
        document_ids=(chunk.document_id,),
    )

    result = run_retrieval_agent(
        run_input,
        retriever=FakeRetriever((chunk,)),
        min_score=0.5,
    )

    assert result.insufficient_evidence is True
    assert result.sources == ()
