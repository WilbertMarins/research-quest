FROM python:3.12.15-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/apps/api/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY apps/api/src ./apps/api/src

EXPOSE 8000

CMD ["uvicorn", "research_quest_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
