from uuid import UUID

from sqlalchemy.orm import Session

from research_quest_api.agent.contracts import AgentResult, AgentRunInput
from research_quest_api.agent.generation import AnswerGenerator
from research_quest_api.agent.graph import run_grounded_agent
from research_quest_api.retrieval import ChunkRetriever
from research_quest_api.tasks.repository import TaskRepository


class AgentTaskExecutor:
    def __init__(
        self,
        *,
        session: Session,
        retriever: ChunkRetriever,
        generator: AnswerGenerator,
        top_k: int = 5,
        min_score: float = 0.25,
    ) -> None:
        self._session = session
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k
        self._min_score = min_score

    def execute(self, task_id: UUID, *, trace_id: str) -> AgentResult:
        repository = TaskRepository(self._session)
        task = repository.start(task_id, trace_id=trace_id)
        run_input = AgentRunInput(
            task_id=task.id,
            question=task.question,
            document_ids=task.document_ids,
        )
        self._session.commit()

        result = run_grounded_agent(
            run_input,
            retriever=self._retriever,
            generator=self._generator,
            top_k=self._top_k,
            min_score=self._min_score,
        )

        repository.complete(
            task_id,
            result=result.model_dump(mode="json"),
        )
        self._session.commit()
        return result
