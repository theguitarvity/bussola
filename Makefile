# Bússola — comandos do repositório (contratos §2). Detalhes em CLAUDE.md.
# Requer `uv` e Python 3.12 (`uv python install 3.12`).

UV ?= uv
PORT ?= 8080
ADK_PORT ?= 8000

# Só entram no lint os diretórios que existem (data/ e deploy/ chegam durante o ciclo).
LINT_MCP := mcp_server $(wildcard data)
LINT_AGENT := agent $(wildcard deploy)

.DEFAULT_GOAL := help
.PHONY: help test test-mcp test-agent lint lint-mcp lint-agent mcp agent fixtures test-bq

help:
	@echo "make test      pytest nos dois projetos (BUSSOLA_FAKES=TRUE, offline)"
	@echo "make lint      ruff check + ruff format --check nos dois projetos"
	@echo "make mcp       sobe o MCP mock em http://localhost:$(PORT)/mcp"
	@echo "make agent     sobe o agente local com ADK Web (porta $(ADK_PORT))"
	@echo "make fixtures  regenera contracts/fixtures/ (ARGS=--sintetico p/ dados de teste)"
	@echo "make test-bq   testes que exigem BigQuery real (@pytest.mark.bq)"

test: test-mcp test-agent

test-mcp:
	cd mcp_server && BUSSOLA_FAKES=TRUE $(UV) run pytest -m "not bq"

test-agent:
	cd agent && BUSSOLA_FAKES=TRUE $(UV) run pytest -m "not bq"

lint: lint-mcp lint-agent

lint-mcp:
	$(UV) run --project mcp_server ruff check $(LINT_MCP)
	$(UV) run --project mcp_server ruff format --check $(LINT_MCP)

lint-agent:
	$(UV) run --project agent ruff check $(LINT_AGENT)
	$(UV) run --project agent ruff format --check $(LINT_AGENT)

mcp:
	cd mcp_server && BUSSOLA_FAKES=TRUE PORT=$(PORT) $(UV) run python -m bussola_mcp.server

agent:
	cd agent && $(UV) run adk web --port $(ADK_PORT) .

fixtures:
	PYTHONPATH=mcp_server $(UV) run --project mcp_server python data/scripts/gerar_fixtures.py $(ARGS)

# pytest sai com 5 quando nenhum teste é coletado; isso não é falha aqui.
test-bq:
	cd mcp_server && $(UV) run pytest -m bq; rc=$$?; [ $$rc -eq 0 ] || [ $$rc -eq 5 ] || exit $$rc
	cd agent && $(UV) run pytest -m bq; rc=$$?; [ $$rc -eq 0 ] || [ $$rc -eq 5 ] || exit $$rc
