from fastapi import FastAPI

from research_quest_api.documents.router import router as documents_router
from research_quest_api.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Research Quest API",
    version="0.1.0",
)

app.state.settings = settings
app.include_router(documents_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
