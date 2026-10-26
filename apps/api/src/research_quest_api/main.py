from fastapi import FastAPI

from research_quest_api.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Research Quest API",
    version="0.1.0",
)

app.state.settings = settings


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
