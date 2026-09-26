# CLAUDE.md — Bússola

PoC da Bússola (Batalha de Agentes Itaú × Google, Grupo 07): jornada agentic
OBJETIVO → ENTENDER → ANTECIPAR → ORIENTAR → AGIR → ACOMPANHAR sobre uma base **sintética**, em dois serviços
Cloud Run (`bussola-mcp` e `bussola-agent`) e BigQuery. Produto e escopo: `docs/contexto-spec-master.md`.
Arquitetura: `docs/blueprint-arquitetura.md`. **Os contratos entre ciclos:** `docs/ciclos/contratos.md`.

> Este arquivo é do repositório da Bússola. Não confunda com convenções de outros projetos.

## Comandos

Requer `uv` e Python 3.12 (`uv python install 3.12`). Tudo roda da raiz.

| Comando | O que faz |
|---|---|
| `make test` | `pytest` nos dois projetos com `BUSSOLA_FAKES=TRUE`, **offline** (só loopback) |
| `make lint` | `ruff check` + `ruff format --check` nos dois projetos (config única em `ruff.toml`) |
| `make mcp` | sobe o MCP (mock no ciclo 000) em `http://localhost:8080/mcp` |
| `make agent` | sobe o agente local com a ADK Web UI (porta 8000); exige `BUSSOLA_MODEL` |
| `make fixtures` | regenera `contracts/fixtures/` da base real (exige `gcloud`/ADC); `ARGS=--sintetico` gera dados de teste |
| `make test-bq` | testes `@pytest.mark.bq` (BigQuery real / fixtures reais); pulam sem credenciais |

## Modo fake

`BUSSOLA_FAKES=TRUE` faz MCP e agente usarem `fakes.py` e `contracts/fixtures/`, sem nenhuma chamada ao GCP. É o
padrão dos testes. `BUSSOLA_MODEL` (ID do Gemini Flash) vem do ambiente e é validado por `deploy/smoke_modelos.py`;
sem ele, e sem o modo fake, o agente não sobe. Variáveis: `contracts/env.example` (sem segredos).

## Onde ficam os contratos

- Texto canônico: `docs/ciclos/contratos.md`. Código: `contracts/` (DDL, `env.example`, fixtures),
  `mcp_server/bussola_mcp/{contratos,dominio/interfaces,dominio/fakes}.py`, `agent/bussola_agent/{estado,callbacks,extensoes,persistencia,mcp_conexao}.py`.
- Mudança de contrato **só por PR** com título `contracts: <mudança>`, aditiva, com o documento e o código no mesmo
  commit e revisão de um ciclo consumidor. Versão: tag `contratos-v1`.

## Propriedade de diretórios

Cada ciclo escreve **somente** nos seus caminhos: tabela em [`docs/ciclos/contratos.md` §1](docs/ciclos/contratos.md).
`pyproject.toml` e `Makefile` aceitam acréscimos de qualquer ciclo (conflito = união das linhas). Só o 001 escreve
em `bussola_dados` e só o 002 em `bussola_rag`.

## Regras que nunca se quebram (constituição: `.specify/memory/constitution.md`)

- O LLM **não calcula nem inventa números**: todo valor vem de ferramenta determinística, com a fonte citada.
- Acesso a dados **somente leitura** e sempre com escopo de `id_usuario` (UUID validado). O agente não vê SQL.
- **Proibido SQL montado por concatenação/f-string** com texto do usuário ou do modelo: sempre parametrizado
  (`@id_usuario`, `@ate_anomes`). Um teste (`test_politicas_repo.py`) vigia isso.
- **Proibido logar** prompt completo, texto de lançamentos, chaves ou tokens: o logger JSON só emite campos de
  contratos §9. **Nunca** versione nem imprima o valor de `gemini-api-key` ou de qualquer token (o mesmo teste vigia).
- Só dados sintéticos; consentimento explícito e auditado para ação sensível; textos ao cliente em pt-BR.
- Testes **só gravam** em `bussola_app_dev`. Cloud Run: `--tag cNNN --no-traffic`; só o ciclo 007 move tráfego.

## Fluxo de PR

1. **1 ciclo = 1 worktree = 1 branch = 1 sessão = 1 execução do Spec Master = 1 feature**
   (`git worktree add ../bussola-NNN -b NNN-slug`; detalhes em `docs/ciclos/README.md` §5–§6).
2. Antes do PR: rebase em `main`, `make lint` e `make test` verdes, critérios de aceite do ciclo.
3. PR para `main` na ordem de merge de `docs/ciclos/README.md` §7, revisado por outra pessoa do time
   (o do ciclo 000 por pelo menos 2). `.spec-master/` é local (gitignored); a rastreabilidade do ciclo vai para
   `specs/NNN-*/traceability.md`.
4. Não dependa de código não mergeado: use `BUSSOLA_FAKES=TRUE` e as fixtures.

## Estrutura

```text
contracts/   DDL, env.example, fixtures      data/scripts/   aplicar_ddl.py, gerar_fixtures.py
mcp_server/  serviço MCP (bussola_mcp/)      agent/          serviço do agente (bussola_agent/)
deploy/      build, deploy, IAM, smoke        specs/          especificações por ciclo (Spec Kit)
```
