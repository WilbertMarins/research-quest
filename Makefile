COMPOSE := docker compose
UV := uv
NPM := npm
WEB_DIR := apps/web

.DEFAULT_GOAL := help

.PHONY: help install up start down restart logs ps build migrate lint format format-check

help:
	@echo "make install       Instala as dependencias locais da API e da web"
	@echo "make up            Sobe PostgreSQL, API e web em primeiro plano"
	@echo "make start         Sobe todo o ambiente em segundo plano"
	@echo "make down          Encerra os servicos sem apagar os dados"
	@echo "make restart       Reinicia todo o ambiente em segundo plano"
	@echo "make logs          Acompanha os logs de todos os servicos"
	@echo "make ps            Exibe o estado dos servicos"
	@echo "make build         Constroi as imagens dos servicos"
	@echo "make migrate       Aplica as migracoes pelo container da API"
	@echo "make lint          Verifica o codigo Python com Ruff"
	@echo "make format        Formata o codigo Python com Ruff"
	@echo "make format-check  Verifica a formatacao sem alterar arquivos"

install:
	$(UV) sync --dev
	$(NPM) --prefix $(WEB_DIR) ci

up:
	$(COMPOSE) up --build

start:
	$(COMPOSE) up --build --detach

down:
	$(COMPOSE) down

restart: down start

logs:
	$(COMPOSE) logs --follow

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

format-check:
	$(UV) run ruff format --check .
