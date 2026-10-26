# Migrações

Migrações versionadas do PostgreSQL e pgvector, gerenciadas com Alembic.

Com o PostgreSQL disponível e o `DATABASE_URL` configurado:

```bash
uv run alembic upgrade head
```

O container da API aplica migrações pendentes antes de iniciar o servidor.
