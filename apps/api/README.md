# Research Quest API

Backend FastAPI responsável pelos contratos HTTP, casos de uso, persistência e execução do fluxo de pesquisa.

## Desenvolvimento local

Na raiz do repositório, instale as dependências:

```bash
uv sync --dev
```

Copie `.env.example` para `.env` e preencha apenas os valores locais necessários. O health check não exige uma chave Groq; a chave é validada quando uma geração real é solicitada.

Inicie a API:

```bash
uv run fastapi dev apps/api/src/research_quest_api/main.py
```

O health check fica disponível em `GET http://127.0.0.1:8000/health`.

O teste automatizado correspondente está em `tests/unit/api/test_health.py`, mas não é executado automaticamente neste fluxo.
