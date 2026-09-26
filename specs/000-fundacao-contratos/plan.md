# Implementation Plan: Fundação e contratos

**Branch**: `000-fundacao-contratos` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/000-fundacao-contratos/spec.md` (com `## Clarifications` de 2026-09-26)

## Summary

Entregar o esqueleto executável da Bússola e materializar os contratos v1 (`docs/ciclos/contratos.md`) em código, para que os
ciclos 001–007 rodem em paralelo. Abordagem: dois projetos `uv` (Python 3.12) independentes, `mcp_server/` (FastMCP, mock sobre
fixtures) e `agent/` (Google ADK, agente *hello* e pontos de extensão), mais `contracts/` (DDL, `env.example`, fixtures),
scripts de dados e de plataforma, `Makefile`, `CLAUDE.md` e a constituição. Tudo que roda no `make test` é **offline**
(`BUSSOLA_FAKES=TRUE`, sem rede nem GCP). O que exige GCP ao vivo (AC4, AC7, AC11–AC13) é entregue como script/teste offline
e **pendência declarada** (decisão D-001). Decisões técnicas e alternativas: [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (`uv`; `requires-python >=3.12,<3.13`); Bash para `deploy/*.sh`; SQL (DDL BigQuery)

**Primary Dependencies**: `mcp_server/`: `fastmcp>=4,<5`, `pydantic>=2.13,<3`, `google-cloud-bigquery>=3.45,<4`, `numpy>=2.5,<3`; `agent/`: `google-adk>=2.10,<3`, `google-genai>=2,<3`, `google-auth`, `mcp>=2.2,<3`, `pydantic>=2.13,<3`; ambos (dev): `pytest>=9,<10`, `pytest-asyncio>=1.4,<2`, `ruff>=0.16,<0.17` — versões e alternativas em `research.md` R1, R3, R15

**Storage**: N/A no runtime do 000 (fixtures JSON versionadas; `RegistroEmMemoria`). BigQuery só nos scripts (`aplicar_ddl.py`, `gerar_fixtures.py`) e nos testes `@pytest.mark.bq`

**Testing**: `pytest` (+ `pytest-asyncio`); `fastmcp.Client` em memória para o mock; um subprocesso local do mock para o AC6; `ruff check` + `ruff format --check`

**Target Platform**: Cloud Run `us-central1`, imagens `linux/amd64` (`python:3.12-slim` + `uv`), `PORT=8080`; desenvolvimento em Linux/macOS

**Project Type**: dois serviços (MCP server + agente ADK) num monorepo, mais scripts de dados/plataforma

**Performance Goals**: não definidos pelo contexto (mestre §12) — N/A

**Constraints**: offline no `make test`; SQL parametrizado; nunca imprimir/versionar segredos; sem `--source`/`adk deploy` (sem bucket); serviços GCP restritos pela org policy; escrita só nos caminhos do 000 (contratos §1)

**Scale/Scope**: ~45 arquivos de código/config, 8 ferramentas MCP, 12 tabelas, 2 usuários × 12 meses de fixtures

## Constitution Check

*GATE: passar antes da Fase 0; reavaliado após a Fase 1.* Constituição `1.0.0` (rascunho, ratificação pendente).

| Princípio | Como o plano atende | Status |
|---|---|---|
| I. Números só de ferramentas determinísticas | O 000 não tem lógica de negócio; os goldens vêm de referência determinística (funções puras) e são marcados provisórios; o agente *hello* não calcula | ✅ |
| II. Escopo por cliente, somente leitura | `gerar_fixtures.py` usa consulta parametrizada somente leitura; o mock exige UUID válido e nunca devolve dado do âncora ao controle; nenhum SQL exposto | ✅ |
| III. Respostas rotuladas e explicáveis | Envelope `fonte` (ferramenta, tabelas, período) em todo golden; instrução mínima do *hello* pede citar a fonte | ✅ |
| IV. Dados sintéticos, consentimento, segredos | Só dados sintéticos; `test_sem_segredos`; `gemini-api-key` só por nome; `iam_datasets.sh` exige confirmação humana em `/dev/tty` | ✅ |
| V. Testes obrigatórios | Suíte offline cobre contratos, mock, callbacks, extensões, persistência, DDL; `bq` fora do padrão | ✅ |
| VI. Contratos versionados e aditivos | As correções em `contratos.md` (Q-001…Q-004, Q-008, Q-010) são aditivas e entram no **mesmo commit** do código; tag `contratos-v1` no merge | ✅ |
| VII. Paralelismo seguro | Só caminhos do 000; sem depender de outro ciclo; `deploy.sh` usa sempre `--tag c000 --no-traffic` (research R14). **Risco condicional:** se o `gcloud` recusar `--no-traffic` na criação de um serviço novo (não verificado aqui), o desvio é registrado em `deploy.md` | ✅ (⚠️ condicional, ver Complexity Tracking) |

Reavaliação pós-design (Fase 1): sem novas violações. A única tensão (VII) já está justificada abaixo.

## Project Structure

### Documentation (this feature)

```text
specs/000-fundacao-contratos/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── marcos.md · questoes.md · checklists/requirements.md
├── tasks.md              # /speckit-tasks
├── traceability.md       # exportado no fim (regra do ciclo)
└── pedidos-owner.md · modelos.md · smoke.md · deploy.md   # entregáveis do ciclo (modelos/smoke/deploy = pendência GCP)
```

`contracts/` desta pasta **não** é criado: os contratos de interface já são `docs/ciclos/contratos.md` (canônico) e o código que este ciclo escreve.

### Source Code (repository root)

```text
CLAUDE.md · Makefile · ruff.toml · .dockerignore · .gitignore (acrescido)
contracts/
├── bigquery/{bussola_dados,bussola_rag,bussola_app}.sql
├── env.example
└── fixtures/{usuarios.json, bussola_dados/, ferramentas/, rag/trechos_exemplo.json}
data/scripts/{aplicar_ddl.py, gerar_fixtures.py}
mcp_server/
├── pyproject.toml · uv.lock · Dockerfile
├── bussola_mcp/{__init__, contratos, logging_json, server}.py
├── bussola_mcp/dominio/{__init__, interfaces, fakes}.py
└── tests/{conftest.py, contrato/…}
agent/
├── pyproject.toml · uv.lock · Dockerfile
├── bussola_agent/{__init__, agent, estado, callbacks, extensoes, persistencia, mcp_conexao, logging_json}.py
└── tests/{conftest.py, contrato/…}
deploy/{build_push.sh, deploy.sh, iam_datasets.sh, smoke_modelos.py}
```

**Structure Decision**: o mapa de contratos §1, restrito aos itens marcados 000, sem `web/` (D-002). Projetos `uv` sem pacote instalável, layout plano
(R5). Testes dos scripts de `data/` e `deploy/` ficam em `mcp_server/tests/contrato/` (dono 000). Dois projetos rodam `ruff` com o mesmo `ruff.toml` da raiz.

## Change plan (por componente)

Cada linha: **componente · responsabilidade · razão · testes · riscos · requisitos**.

| # | Componente | Responsabilidade | Razão | Testes | Riscos | Requisitos |
|---|---|---|---|---|---|---|
| C1 | `CLAUDE.md`, `Makefile`, `ruff.toml`, `.dockerignore`, `.gitignore`(+) | Convenções, targets `test/lint/mcp/agent/fixtures/test-bq`, lint único, contexto de build enxuto | Onboarding e gates | `make test`/`make lint` rodam; `test-bq` tolera "0 testes" (código 5) | `make` chamando `uv` sem 3.12 → mensagem clara no `CLAUDE.md` | FR-002/003/004 · AC1, AC2 |
| C2 | `mcp_server/` e `agent/` (`pyproject.toml`, `uv.lock`, `Dockerfile`) | Dependências e imagens por serviço | Um projeto por serviço Cloud Run | `uv sync --frozen`; build local da imagem (se Docker disponível) | `ghcr.io`/PyPI bloqueados; contexto de build na raiz (R6) | FR-005 · AC3, AC13 |
| C3 | `contracts/bigquery/*.sql`, `contracts/env.example` | DDL idempotente com `{project}/{dataset}`; variáveis sem segredo | Contrato de dados e de configuração | DDL↔modelos; `--dry-run` do `aplicar_ddl`; `test_sem_segredos` | IDs de modelo vazios até o smoke (R8) | FR-006/007 · AC3, AC12 |
| C4 | `bussola_mcp/contratos.py` | Modelos de linha, entrada, `dados`, envelopes, `CodigoErro`, `Trecho` | Fonte única dos schemas | DDL↔modelos; validação de todas as fixtures/goldens | Deriva de contratos §3/§5 → teste com tabela literal de §5 | FR-008 · AC3 |
| C5 | `dominio/interfaces.py`, `dominio/fakes.py` | `Protocol`s de §4; fakes sobre fixtures (`RepositorioFake`, `BuscadorFake`) com o filtro de escopo de §3 | 001–004 trabalham sem BigQuery | `perfil_mensal(controle, 202503)` = 3 meses só do controle; `isinstance` dos Protocols; filtro do buscador | Buscador fake ingênuo (palavras em comum) — marcado como fake | FR-009 · AC3 |
| C6 | `logging_json.py` (×2) | JSON por linha com campos de §9; **whitelist** de campos | Cloud Logging + nunca logar prompt/segredos | campos e `severity`; campo proibido (`prompt`, `texto`) não sai | Duplicação entre serviços (intencional: serviços independentes) | FR-010 |
| C7 | `agent/estado.py`, `callbacks.py`, `extensoes.py`, `persistencia.py` | Chaves/enum; encadeador (R4); registro de extensões; `RegistroApp` + modelos + `RegistroEmMemoria` | Evitar conflito 004/005/006 no `agent.py` | AC8, AC9, AC10 (ver Test strategy); DDL↔modelos de `bussola_app` | Semântica async do ADK 2.10 (R4) | FR-011…014 · AC8–AC10 |
| C8 | `agent/mcp_conexao.py` | `MCPToolset` (URL, OIDC opcional por `header_provider`) e `chamar_ferramenta` com escopo forçado | 004/006 falam com o MCP | AC6 contra o mock em subprocesso local; escopo forçado (o modelo não escolhe `id_usuario`) | OIDC com ADC de usuário não funciona (R3) | FR-015 · AC6 |
| C9 | `data/scripts/gerar_fixtures.py`, `contracts/fixtures/**` | Busca das linhas brutas, agregação única, goldens de referência, modo `--sintetico`, `origem` em `usuarios.json` | Fixtures reproduzíveis e testáveis offline (R9, R10) | modo sintético determinístico; todo arquivo validado pelos modelos; **1% do âncora só com base real** (`bq`) | Nomes reais das categorias desconhecidos; regras provisórias (R9) | FR-016/017 · AC4 (pendente) |
| C10 | `bussola_mcp/server.py` | Mock FastMCP `/mcp`: 8 ferramentas, validação, golden por corte, controle → `DADOS_INSUFICIENTES`, logs | 004/006/007 sem MCP real | AC5 completo (lista, schema×§5, erros, cortes) | FastMCP valida tipos por conta própria (R2); `host_origin_protection` no Cloud Run (validar no deploy) | FR-018/019 · AC5 |
| C11 | `agent/bussola_agent/agent.py`, `__init__.py` | `root_agent` mínimo pt-BR; 4 callbacks agregados; `carregar_extensoes()`; `BUSSOLA_MODEL` do ambiente | Ponto de partida do 004 | import em `BUSSOLA_FAKES=TRUE`; 4 callbacks instalados; toolset presente; instrução em pt-BR | Falha sem `BUSSOLA_MODEL` (intencional, R7) | FR-020 · AC7 (smoke com LLM pendente) |
| C12 | `data/scripts/aplicar_ddl.py` | Cria 4 datasets + tabelas, idempotente; `--dry-run` | Plataforma reprodutível | dry-run: 4 `CREATE SCHEMA` + tabelas, todos `IF NOT EXISTS` | Execução real precisa de ADC (pendente) | FR-021 · AC11 (pendente) |
| C13 | `deploy/smoke_modelos.py` | Primeiro Flash que responde + embedding (dimensão/latência); escreve `env.example` e `modelos.md`; fallback API key via `gcloud secrets` sem imprimir | Risco de ID de modelo (mestre §17) | funções puras: escolha do primeiro que responde, reescrita de `env.example`, nunca imprime a chave | IDs candidatos são suposições (R8) | FR-022 · AC12 (pendente) |
| C14 | `deploy/build_push.sh`, `deploy.sh`, `iam_datasets.sh` | Build `linux/amd64` + push AR; deploy sempre com `--tag c000 --no-traffic` (fallback documentado só se o `gcloud` recusar na criação); Plano B de IAM com confirmação humana em `/dev/tty` | Pipeline validado cedo | `bash -n`; sem flag que pule a confirmação; modo `DRY_RUN=1` imprime os comandos | Só executável com `gcloud`/`docker` autenticados (pendente) | FR-023/024 · AC13 (pendente) |
| C15 | `specs/000-*/pedidos-owner.md`, `questoes.md`, `traceability.md`; edições em `docs/ciclos/contratos.md` | Pedidos prontos p/ envio (4 itens), decisão Plano A/B "pendente", registro de lacunas e correções de contrato | Regra do ciclo §1.5 | revisão humana; teste de `contratos.md` ↔ código onde mecânico | O agente não envia mensagens | FR-025/027/028/029/030 · AC14, AC15 |

**Correções de `docs/ciclos/contratos.md` no mesmo PR** (todas aditivas): §8 — entradas fixas dos goldens, comportamento do mock para o controle, `origem` em `usuarios.json`,
`buscar_contexto_financeiro` via `BuscadorFake`; §6 — `extensoes.sensiveis()`; §2/§4 — `fastmcp` como biblioteca do servidor.

## Test strategy

- **Unidade/contrato (`make test`, offline):** DDL↔modelos (dados, rag no `mcp_server`; app no `agent`); fixtures/goldens validados pelos modelos; fakes; mock via `fastmcp.Client(mcp)` (lista as 8 ferramentas, schema×§5 com tabela literal, golden 202506/202512 + aviso de mock, UUID desconhecido/malformado, `ate_anomes=202601`, prazo+aporte juntos, controle → `DADOS_INSUFICIENTES`, `resumo_mes`); encadeador (4 fases, ordem 10 impede 20, síncrono e assíncrono, exceção propaga); extensões (pacote ausente ok; `ImportError` interno propaga; faixas de instrução); persistência (`isinstance(RegistroEmMemoria(), RegistroApp)`, ida e volta); logging (whitelist); `gerar_fixtures --sintetico` determinístico; `aplicar_ddl --dry-run`; funções puras do `smoke_modelos`; `bash -n` dos `.sh`; `test_sem_segredos`.
- **Integração local sem LLM (AC6):** o teste do agente sobe `python -m bussola_mcp.server` (subprocesso via `uv run --project ../mcp_server`) numa porta livre e verifica que o `MCPToolset` lista as 8 ferramentas.
- **`bq` (`make test-bq`, fora do padrão):** datasets existem e 1% do âncora contra fixtures **da base real**; pulam sem credenciais.
- **Manual/pendente (GCP):** smoke do agente com LLM (`smoke.md`), `aplicar_ddl` real (2ª execução sem mudança), `smoke_modelos`, build/push/deploy (`deploy.md`).
- **Mecanismos de validação:** `make lint`, `make test`, `traceability.md` mapeando AC→FR→tarefa→teste, `quickstart.md` como roteiro reproduzível.

## Work packages (perfil XL)

Pacotes de `risk work-packages` adaptados a este ciclo (sem novos passos do Spec Kit):

| Pacote | Conteúdo | Dono → revisor | Depende de |
|---|---|---|---|
| `contract` | C3, C4, C5, correções de `contratos.md` | architect → tech-lead | — |
| `data-model` | C4 (modelos), C7 (`persistencia`), C9 (fixtures) | backend-dev → fullstack-dev | contract |
| `backend` | C6, C7, C8, C10, C11, C12, C13, C14 | backend-dev → fullstack-dev | data-model |
| `frontend` | **N/A** — sem front (D-002); o pacote fica registrado como "não aplicável" | — | — |
| `e2e` | AC6 (subprocesso), AC5 completo, suíte inteira verde, `quickstart.md` | qa → tech-lead | backend |
| `docs` | C1 (`CLAUDE.md`), C15 (pedidos, questões, rastreabilidade) | tech-lead → architect | e2e |

## ADRs (perfil XL: verificação obrigatória)

- **ADR-1** `fastmcp` como biblioteca do servidor MCP (R1). Gatilho: nova dependência/provedor.
- **ADR-2** Agregação única em Python para as fixtures, com modo sintético (R9). Gatilho: novo modelo de dados de referência.
- **ADR-3** Serviços Cloud Run criados pelo 000 como **privados**, com `--tag c000 --no-traffic` sempre tentado e fallback registrado (R14). Gatilho: mudança de infraestrutura.

## Complexity Tracking

> Só o que fere a constituição ou o texto do ciclo, com justificativa.

| Violação / desvio | Por que é necessário | Alternativa mais simples rejeitada porque |
|---|---|---|
| **Princípio VII** (`--no-traffic`) — **condicional, não verificado**: se o `gcloud` recusar `--no-traffic` ao criar `bussola-mcp`/`bussola-agent` (suspeita sem confirmação, sem `gcloud` aqui), a primeira revisão recebe tráfego | O ciclo §3.5 manda publicar os dois serviços. O `deploy.sh` tenta sempre `--tag c000 --no-traffic`; só em caso de recusa cria sem a flag (serviço **privado**), avisa e registra o desvio em `deploy.md`. O 000 nunca move tráfego depois | Não publicar reprovaria AC13; pedir a alguém que crie o serviço antes só desloca o problema |
| `fastmcp` no lugar de "`mcp`/FastMCP" (ciclo §3.2) | O `mcp` 2.x renomeou `FastMCP`; o AC5 cita `fastmcp.Client` | `mcp<2` cria dívida imediata; `MCPServer` diverge do AC5 |
| Agregação das fixtures em Python, e não "SQL de referência" (ciclo §3.4) | Uma implementação só, testável offline (R9); o SQL de produção é do 001 | Duas implementações (SQL + Python) divergiriam sem detecção |
| `mcp` como dependência explícita do `agent/` (ciclo §3.2 não lista) | `chamar_ferramenta` importa o cliente do SDK; depender de um transitivo é frágil | Usar `fastmcp` no agente engordaria a imagem sem necessidade |
