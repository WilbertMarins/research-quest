# Research Quest — MVP orientado a especificações

Especificações de produto e implementação para a PoC **Research Quest**.

## Objetivo

Construir uma aplicação em que uma pessoa envia documentos e perguntas, um agente com RAG produz respostas fundamentadas em fontes, e a interface acompanha o ciclo de vida da tarefa.

## Estado atual

A fundação, a ingestão vertical e o gerenciamento de tarefas estão implementados: a API recebe TXT/MD, persiste embeddings locais e cria, consulta e lista tarefas com uma fotografia dos documentos selecionados. Busca, agente e interface integrada ainda serão implementados.

## Stack do MVP

- Python 3.12+
- FastAPI para API HTTP
- LangGraph para o fluxo do agente
- LangChain para integrações de LLM, embeddings e retrievers
- PostgreSQL com pgvector para persistência e busca vetorial
- Executor em background com contrato preparado para Celery + RabbitMQ
- Logs correlacionados; Langfuse é secundário
- Next.js + TypeScript para interface
- Docker Compose para ambiente local
- GNU Make para atalhos de desenvolvimento
- Ruff para lint e formatação do código Python
- pytest para testes

## Estrutura do monorepo

```text
apps/
├── api/                 # FastAPI e casos de uso
└── web/                 # Next.js e interface
infra/
└── docker/              # Arquivos auxiliares de containers
migrations/              # Migrações PostgreSQL/pgvector
packages/
└── contracts/           # Contratos compartilhados entre API e frontend
tests/
├── unit/
├── integration/
└── e2e/
```

## Como usar estas specs

1. Leia `research-quest-specs/specs/10-mvp-delivery/spec.md`.
2. Revise `research-quest-specs/specs/10-mvp-delivery/design.md`.
3. Execute as tarefas de `research-quest-specs/specs/10-mvp-delivery/tasks.md` em ordem.
4. Para cada atividade, implemente apenas o escopo definido e revise o diff sem executar testes.
5. Não avance para a próxima atividade enquanto os critérios da atual não estiverem atendidos.
6. Registre decisões arquiteturais relevantes em `research-quest-specs/decisions/`.

## Pré-requisitos

- Docker com Compose.
- GNU Make.
- Para desenvolvimento fora dos containers: Python 3.12 e `uv`.
- Para desenvolvimento do frontend fora dos containers: Node.js 20.9 ou superior e npm.

## Configuração local

Crie o arquivo local de ambiente sem versioná-lo:

```powershell
Copy-Item .env.example .env
```

Em Linux ou macOS, use `cp .env.example .env`. As credenciais do exemplo servem somente para desenvolvimento local. Preencha `GROQ_API_KEY` antes de usar geração real de respostas.

## Inicialização com Docker

Para subir PostgreSQL, API e frontend juntos, com os logs no terminal:

```bash
make up
```

A API fica disponível em `http://localhost:8000`, o frontend em `http://localhost:3000` e o PostgreSQL/pgvector em `localhost:5432`. Credenciais padrão são apenas locais e podem ser substituídas no `.env`.

O container da API aplica migrações pendentes antes de iniciar. Para executar em segundo plano ou encerrar os serviços sem remover os dados persistidos:

```bash
make start
make down
```

Outros atalhos disponíveis:

```bash
make help       # lista todos os comandos
make build      # constrói as imagens
make logs       # acompanha os logs
make ps         # mostra o estado dos serviços
make restart    # reinicia o ambiente em segundo plano
make migrate    # aplica as migrações pelo container da API
make ci         # executa localmente as verificações da CI
```

Os comandos `make up` e `make start` incluem os três serviços definidos no Compose: PostgreSQL, API e web.

## Desenvolvimento sem containers de aplicação

Mantenha o PostgreSQL disponível e inicie a API na raiz:

```bash
make install
uv run alembic upgrade head
uv run fastapi dev apps/api/src/research_quest_api/main.py
```

Em outro terminal, inicie o frontend:

```bash
npm --prefix apps/web run dev
```

## Upload e indexação de documentos

Envie um arquivo como `multipart/form-data` no campo `file`:

```bash
curl -X POST http://localhost:8000/api/documents \
  -F "file=@notes.md;type=text/markdown"
```

Formatos aceitos: `.txt` com `text/plain` e `.md` com `text/markdown` ou `text/plain`. O conteúdo deve ser UTF-8, não pode conter somente espaços e deve respeitar `MAX_UPLOAD_BYTES` — 2 MiB por padrão.

Um documento novo retorna HTTP `201`, estado `completed`, quantidade de chunks e `created: true`. Conteúdo idêntico é detectado por SHA-256 e retorna o registro existente com HTTP `200` e `created: false`; o conteúdo integral nunca aparece na resposta.

Erros públicos possíveis:

- `413 file_too_large`: arquivo acima do limite configurado;
- `415 unsupported_extension` ou `unsupported_media_type`: formato não aceito;
- `422 invalid_encoding`, `empty_document` ou `chunk_limit_exceeded`;
- `503 embedding_failed`: falha sanitizada ao gerar embeddings locais.

O primeiro upload pode baixar o modelo configurado em `EMBEDDING_MODEL`. O MVP utiliza `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, vetores de 384 dimensões e PyTorch CPU-only. Trocar modelo ou dimensão exige reindexação explícita; não altere apenas `EMBEDDING_DIMENSION` em uma base existente.

O contrato interativo fica disponível em `http://localhost:8000/docs`.

## Tarefas de pesquisa

Crie uma tarefa com uma pergunta e, opcionalmente, os UUIDs de documentos que já estejam em estado `completed`:

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"question":"Quais são os principais pontos?","document_ids":[]}'
```

Quando `document_ids` for omitido ou estiver vazio, a API seleciona todos os documentos concluídos disponíveis naquele instante. Essa seleção é persistida na tarefa e não muda com uploads posteriores. A criação retorna HTTP `201` e estado `queued`; a execução do agente será conectada em uma etapa posterior.

Consulte uma tarefa ou liste as mais recentes:

```bash
curl http://localhost:8000/api/tasks/UUID_DA_TAREFA
curl "http://localhost:8000/api/tasks?limit=20&offset=0"
```

A listagem ordena da mais nova para a mais antiga, aceita `limit` entre 1 e 100 e informa `has_more`. Os estados públicos são `queued`, `running`, `waiting_for_tool`, `retrying`, `completed` e `failed`. ID inexistente retorna `404 task_not_found`; pergunta vazia ou seleção de documentos inválida retorna HTTP `422`.

## Migrações

Crie uma revisão somente depois de alterar os modelos persistentes:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Não edite uma migração que já tenha sido aplicada em ambientes compartilhados; crie uma nova revisão.

## Qualidade do código Python com Ruff

Ruff é usado como linter e formatador. Os comandos são sempre manuais e não executam testes:

```bash
make lint          # equivale a: uv run ruff check .
make format-check  # equivale a: uv run ruff format --check .
make format        # equivale a: uv run ruff format .
```

`make format` altera os arquivos Python; `make lint` e `make format-check` apenas verificam.

## Integração contínua com GitHub Actions

O workflow `.github/workflows/ci.yml` é executado em pull requests, pushes para `main` e acionamentos manuais. Ele instala versões fixas de Python, `uv` e Node.js e então executa `make ci`, que verifica:

- lint e formatação do Python com Ruff;
- tipos do frontend com TypeScript;
- build de produção do frontend.

As suítes `pytest` e Vitest não fazem parte da CI enquanto vigorar a regra de não executar testes automaticamente.

Para executar exatamente os comandos de qualidade e build antes de enviar ao GitHub:

```bash
make ci
```

Para simular o próprio workflow localmente, instale o [`act`](https://nektosact.com/installation/) e mantenha o Docker em execução. No Windows:

```powershell
winget install nektos.act
```

Depois, liste os jobs ou execute o evento de pull request com logs no terminal:

```bash
make ci-act-list
make ci-act
```

Os comandos equivalentes são `act pull_request --list --workflows .github/workflows/ci.yml` e `act pull_request --workflows .github/workflows/ci.yml`. A simulação do `act` é útil, mas não é idêntica aos runners hospedados pelo GitHub; a confirmação definitiva continuará aparecendo na aba **Actions** do repositório após o push.

## Testes — apenas referência

Os testes são criados com cada incremento, mas não são executados automaticamente neste fluxo. Os comandos previstos são:

```bash
uv run pytest
cd apps/web && npm test
```

Até que haja uma execução manual registrada, o estado da suíte deve ser considerado **não executado**, nunca aprovado implicitamente.

## Política de trabalho

- Preferir commits lógicos com **500 linhas alteradas ou menos**.
- Dividir tarefas que provavelmente excedam esse limite.
- Não executar testes durante este fluxo; registrar a validação automatizada como não executada.
- Tratar `research-quest-specs/` como referência local e não incluir seus arquivos em commits.
- Não incluir arquivos gerados, segredos, dependências vendorizadas ou alterações sem relação com a tarefa.
- Não implementar funcionalidades fora das specs sem alinhar o escopo primeiro; eventuais ajustes nas specs permanecem locais e não são versionados.
- Não fazer chamadas reais a provedores de LLM nos testes unitários.
- Usar mocks/fakes nos testes e reservar integrações reais para testes explicitamente configurados.

## Ordem de implementação do MVP

1. Fundação, configuração e ambiente local.
2. Ingestão de documentos e chunking.
3. Embeddings locais e busca vetorial.
4. Modelo, API e seleção de documentos das tarefas.
5. Grafo do agente e resposta fundamentada via Groq.
6. Execução em background e estados persistidos.
7. Interface para upload, pergunta, polling, fontes e histórico.
8. Cobertura automatizada não executada e documentação final.

SSE, Langfuse, Celery/RabbitMQ e pixel art entram depois do fluxo vertical, desde que não comprometam a entrega do MVP.

## Escopo da primeira PoC

A PoC é para um único usuário local, sem autenticação, billing, multi-tenancy ou implantação em produção. A arquitetura deve permitir evolução, mas não deve antecipar complexidade sem necessidade.
