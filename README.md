# Research Quest — SDD

Especificações de produto e implementação para a PoC **Research Quest**.

## Objetivo

Construir uma aplicação em que uma pessoa envia documentos e perguntas, um agente com RAG produz respostas fundamentadas em fontes, e a interface acompanha o ciclo de vida da tarefa.

## Stack proposta

- Python 3.12+
- FastAPI para API HTTP
- LangGraph para o fluxo do agente
- LangChain para integrações de LLM, embeddings e retrievers
- PostgreSQL com pgvector para persistência e busca vetorial
- Celery + RabbitMQ para execução assíncrona
- Langfuse para observabilidade
- Next.js + TypeScript para interface
- Docker Compose para ambiente local
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

1. Leia `research-quest-specs/specs/00-foundation/spec.md`.
2. Revise `research-quest-specs/specs/00-foundation/design.md`.
3. Execute as tarefas de `research-quest-specs/specs/00-foundation/tasks.md` em ordem.
4. Para cada atividade, implemente apenas o escopo definido e revise o diff sem executar testes.
5. Não avance para a próxima atividade enquanto os critérios da atual não estiverem atendidos.
6. Registre decisões arquiteturais relevantes em `research-quest-specs/decisions/`.

## Inicialização com Docker

```bash
docker compose up --build
```

A API fica disponível em `http://localhost:8000`, o frontend em `http://localhost:3000` e o PostgreSQL/pgvector em `localhost:5432`. Credenciais padrão são apenas locais e podem ser substituídas no `.env`.

## Política de trabalho

- Preferir commits lógicos com **500 linhas alteradas ou menos**.
- Dividir tarefas que provavelmente excedam esse limite.
- Não executar testes durante este fluxo; registrar a validação automatizada como não executada.
- Tratar `research-quest-specs/` como referência local e não incluir seus arquivos em commits.
- Não incluir arquivos gerados, segredos, dependências vendorizadas ou alterações sem relação com a tarefa.
- Não implementar funcionalidades fora das specs sem alinhar o escopo primeiro; eventuais ajustes nas specs permanecem locais e não são versionados.
- Não fazer chamadas reais a provedores de LLM nos testes unitários.
- Usar mocks/fakes nos testes e reservar integrações reais para testes explicitamente configurados.

## Ordem de implementação sugerida

1. Fundação, configuração e ambiente local.
2. Modelo e API de tarefas.
3. Ingestão de documentos.
4. Busca vetorial.
5. Grafo de agente e resposta fundamentada.
6. Execução assíncrona e resiliência.
7. Observabilidade.
8. Atualizações ao vivo no frontend.
9. Interface gamificada.
10. Testes ponta a ponta e documentação.

## Escopo da primeira PoC

A PoC é para um único usuário local, sem autenticação, billing, multi-tenancy ou implantação em produção. A arquitetura deve permitir evolução, mas não deve antecipar complexidade sem necessidade.
