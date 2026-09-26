---

description: "Tasks do ciclo 000 — Fundação e contratos"
---

# Tasks: Fundação e contratos

**Input**: `/specs/000-fundacao-contratos/` — `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: **solicitados** (spec FR-026, AC2; constituição V). Em cada história, os testes vêm **antes** e devem falhar antes da implementação.

**Formato**: `[ID] [P?] [Story] Descrição com caminho`. `[P]` = arquivos diferentes, sem dependência pendente.
`[HUMANO-GCP]` = exige `gcloud`/ADC ou decisão humana; **não é executada por este run** (decisão D-001) e fica como pendência declarada.

Todos os comandos rodam na raiz da worktree. Python 3.12 via `uv`. Nenhum segredo é impresso (constituição IV).

## Phase 1: Setup

- [X] T001 [P] Criar `ruff.toml` na raiz (line-length 100, alvo py312, regras `E,F,I,B,UP`) e `.dockerignore` na raiz (excluir `.git`, `.claude`, `.specify`, `.spec-master`, `specs`, `docs`, `**/.venv`, `**/__pycache__`, `**/.pytest_cache`, `**/.ruff_cache`); conferir que o `.gitignore` existente já cobre `.venv`, `.env*`, caches, `.spec-master/` (acrescentar só o que faltar) e que `uv.lock` **não** está ignorado
- [X] T002 Criar `mcp_server/pyproject.toml` (`requires-python >=3.12,<3.13`; deps `fastmcp>=4,<5`, `pydantic>=2.13,<3`, `google-cloud-bigquery>=3.45,<4`, `numpy>=2.5,<3`; grupo dev `pytest>=9,<10`, `pytest-asyncio>=1.4,<2`, `ruff>=0.16,<0.17`; `[tool.uv] package = false`; pytest com `pythonpath = ["."]`, `asyncio_mode = "auto"`, marcador `bq`), `mcp_server/bussola_mcp/__init__.py`, `mcp_server/bussola_mcp/dominio/__init__.py`, `mcp_server/tests/__init__.py`, `mcp_server/tests/contrato/__init__.py` e `mcp_server/tests/conftest.py` (`os.environ.setdefault("BUSSOLA_FAKES", "TRUE")`; fixture autouse que **bloqueia conexões de rede exceto loopback** nos testes sem marcador `bq`); rodar `uv sync --project mcp_server` para gerar `mcp_server/uv.lock`
- [X] T003 [P] Criar `agent/pyproject.toml` (deps `google-adk>=2.10,<3`, `google-genai>=2,<3`, `google-auth>=2.58,<3`, `mcp>=2.2,<3`, `pydantic>=2.13,<3`; mesmo grupo dev/config do T002), `agent/bussola_agent/__init__.py` (vazio por ora), `agent/tests/__init__.py`, `agent/tests/contrato/__init__.py` e `agent/tests/conftest.py` (mesmo `BUSSOLA_FAKES` e mesmo bloqueio de rede); `uv sync --project agent` → `agent/uv.lock`
- [X] T004 Criar `Makefile` na raiz com os targets de contratos §2: `test` (pytest nos dois projetos com `BUSSOLA_FAKES=TRUE`, `-m "not bq"`), `lint` (`ruff check` + `ruff format --check` em `mcp_server`+`data`, e em `agent`+`deploy`), `mcp` (`uv run python -m bussola_mcp.server` na porta 8080), `agent` (`adk web`), `fixtures` (`PYTHONPATH=mcp_server uv run --project mcp_server python data/scripts/gerar_fixtures.py $(ARGS)`), `test-bq` (`pytest -m bq` nos dois projetos, tolerando o código 5 de "nenhum teste coletado")
- [X] T005 Validar o Setup: `make lint` verde nos dois projetos (com os pacotes ainda vazios)

**Checkpoint**: dois projetos `uv` instalados, `make lint` funcionando.

---

## Phase 2: Foundational (bloqueia todas as histórias)

**Propósito**: DDL, modelos e logger que todas as histórias usam.

- [X] T006 [P] Escrever `mcp_server/tests/contrato/test_ddl_modelos.py` (**deve falhar**): parser mínimo de `CREATE TABLE IF NOT EXISTS` (removendo os placeholders `{project}`/`{dataset}`) e comparação `{coluna: tipo}` DDL ↔ modelo Pydantic para as 7 tabelas de `bussola_dados` e `documentos` de `bussola_rag`. Mapa de tipos: `STRING→str`, `INT64→int`, `FLOAT64→float`, `BOOL→bool`, `TIMESTAMP→datetime`, `JSON→dict`, `ARRAY<FLOAT64>→list[float]`; `NOT NULL` ↔ campo sem `| None`
- [X] T007 [P] Criar `contracts/env.example` (as 19 variáveis de contratos §7 (a linha `BQ_DATASET_DADOS`/`RAG`/`APP` conta 3) com os valores padrão/exemplo da tabela; `BUSSOLA_MODEL=` e `EMBEDDING_MODEL=` **vazios** com comentário dos candidatos; `GOOGLE_API_KEY=` **vazio** e comentado como "só Plano B, nunca versionar"; **nenhum valor secreto**) e os arquivos `contracts/bigquery/bussola_dados.sql`, `contracts/bigquery/bussola_rag.sql` e `contracts/bigquery/bussola_app.sql` com as tabelas e colunas de contratos §3: `CREATE SCHEMA IF NOT EXISTS \`{project}.{dataset}\` OPTIONS(location="us-central1")` e `CREATE TABLE IF NOT EXISTS \`{project}.{dataset}.<tabela>\``; colunas `NOT NULL`, **exceto** as marcadas `NULL` em §3 (`documentos.id_usuario`, `documentos.anomes`, `consentimentos.plano_id`, `auditoria.ferramenta`, `acompanhamento.categoria_desvio`, `acompanhamento.acao_sugerida`)
- [X] T008 Criar `mcp_server/bussola_mcp/contratos.py` (depende de T006/T007): modelos `PerfilMes`, `GastoCategoria`, `EntradaCategoria`, `Recorrente`, `Parcela`, `Categoria`, `RefCoorte`, `Documento`; `Periodo`, `Fonte`, `Erro`, `Resposta`, `RespostaErro`, `CodigoErro` (`StrEnum`: `USUARIO_INEXISTENTE`, `ENTRADA_INVALIDA`, `PRAZO_IMPLAUSIVEL`, `DADOS_INSUFICIENTES`, `INDISPONIVEL`), `Trecho`; entrada (`id_usuario: str`, `ate_anomes: int` + adicionais de §5) e `Dados*` de **cada** ferramenta de §5 (incl. `resumo_mes` e `referencia_coorte`), conforme `data-model.md` §2; `T006` passa
- [X] T009 [P] Criar `mcp_server/bussola_mcp/logging_json.py` e `agent/bussola_agent/logging_json.py` (mesmo conteúdo, `servico` diferente): JSON por linha em stdout com `severity` e `message`; **whitelist** dos campos de contratos §9 (`servico`, `session_id`, `estado_jornada`, `ferramenta`, `evento`, `consentimento`, `ate_anomes`, `latencia_ms`, `erro_codigo`); campo fora da lista (ex.: `prompt`, `texto`, `token`) é descartado. Testes primeiro: `mcp_server/tests/contrato/test_logging_json.py` e `agent/tests/contrato/test_logging_json.py`

**Checkpoint**: DDL, modelos e logger prontos; T006 e T009 verdes.

---

## Phase 3: User Story 1 — Ciclo consumidor trabalha sobre contratos congelados (P1) 🎯 MVP

**Objetivo**: interfaces de domínio, fixtures e fakes para os ciclos consumidores rodarem sem GCP.
**Teste independente**: `make test` do `mcp_server` verde offline; fake do controle 202503 devolve 3 meses só do controle.

### Testes (escrever primeiro, devem falhar)

- [X] T010 [P] [US1] `mcp_server/tests/contrato/test_gerar_fixtures.py`: modo sintético é **determinístico** (duas gerações em diretório temporário são idênticas byte a byte); 2 usuários × 12 meses (`202501`–`202512`); `usuarios.json` com `origem = "sintetico_teste"`; toda linha, todo golden, todo `resumo_mes__AAAAMM` e `rag/trechos_exemplo.json` (formato `Trecho`) valida nos modelos de `contratos.py`; `referencia_coorte.json == []`; **modo real com cliente BigQuery falso injetado**: a busca das linhas usa consulta **parametrizada** (`ArrayQueryParameter` para `@ids`), sem interpolar os UUIDs no texto do SQL, e é somente leitura
- [X] T011 [P] [US1] `mcp_server/tests/contrato/test_fakes.py`: `RepositorioFake().perfil_mensal(controle, 202503)` → **3 meses do controle e nenhum do âncora**; `isinstance(RepositorioFake(), RepositorioFinanceiro)` e `isinstance(BuscadorFake(), BuscadorContexto)`; o buscador aplica `(id_usuario = X OR tipo = 'coorte') AND (anomes IS NULL OR anomes <= ate_anomes)` e respeita `k`

### Implementação

- [X] T012 [US1] Criar `mcp_server/bussola_mcp/dominio/interfaces.py`: `RepositorioFinanceiro` e `BuscadorContexto` como `Protocol` (`runtime_checkable`) com as assinaturas exatas de contratos §4
- [X] T013 [US1] Criar `data/scripts/gerar_fixtures.py` (research R9, R10): busca das **linhas brutas** dos 2 usuários por consulta **parametrizada** somente leitura (`WHERE id_usuario IN UNNEST(@ids)`), agregação única em Python (`perfil_mensal`, `gastos_categoria`, `entradas_categoria`, `recorrentes`, `parcelas`, `categorias`; `referencia_coorte = []`), modo `--sintetico` com extrato mínimo determinístico, goldens de referência (6 ferramentas P0 × cortes `202506`/`202512`) e `resumo_mes__AAAAMM` (12 arquivos), `ferramentas/_entradas.json` (`top_n=5`, `valor_alvo=60000.0`, `prazo_meses=36`, `pergunta="quanto gasto com comer fora?"`, `k=5`), `rag/trechos_exemplo.json` (âncora + 1 `coorte`), `usuarios.json` com `origem`; saídas com 2 casas decimais; **valida cada arquivo pelos modelos antes de gravar**; regras provisórias sinalizadas por aviso (Q-006); a referência de métricas/simulação fica **só dentro deste script** — **não** criar `dominio/metricas.py`, `dominio/simulacao.py` nem `repositorio_bq.py` (são do 001); a função de busca aceita o cliente por parâmetro (injeção) para o teste do T010
- [X] T014 [US1] Gerar e versionar as fixtures **sintéticas de teste**: `make fixtures ARGS=--sintetico` → `contracts/fixtures/**` (usuário âncora `36a21505-d6d4-42d3-b319-d51a133c7269`, controle `31e94f2f-1463-49f9-a41a-b3f220ed976a`)
- [X] T015 [US1] Criar `mcp_server/bussola_mcp/dominio/fakes.py`: `RepositorioFake` e `BuscadorFake` sobre `contracts/fixtures/` (diretório configurável por `BUSSOLA_FIXTURES_DIR`, padrão relativo ao repositório); buscador ingênuo e determinístico (palavras em comum), marcado como fake
- [X] T016 [US1] Rodar T006, T010 e T011 → verdes

**Checkpoint**: US1 completa e testável sozinha.

---

## Phase 4: User Story 2 — Mock do MCP serve as ferramentas com os schemas exatos (P1)

**Objetivo**: 8 ferramentas (7 P0 + `resumo_mes`) com assinaturas de contratos §5, respondendo com fixtures.
**Teste independente**: `fastmcp.Client(mcp)` lista 8 ferramentas e devolve golden/erros esperados.

- [X] T017 [P] [US2] `mcp_server/tests/contrato/test_server_mock.py` (**falha primeiro**): lista exatamente as 8 ferramentas `perfil_financeiro`, `capacidade_poupanca`, `oportunidades_corte`, `dividas_e_parcelas`, `simular_objetivo`, `comparar_cenarios`, `buscar_contexto_financeiro`, `resumo_mes`; **schema × tabela literal de §5** (nomes, obrigatórios, tipos simples, defaults: `top_n=5`, `k=5`, `usar_saldo_atual=false`); para **cada uma das 6 ferramentas com golden** (`perfil_financeiro`, `capacidade_poupanca`, `oportunidades_corte`, `dividas_e_parcelas`, `simular_objetivo`, `comparar_cenarios`) com o âncora: `ate_anomes = 202506` → golden `__ate_202506` + aviso de mock, `202512` → `__ate_202512`, e `ate_anomes = 202503` → `__ate_202506` + aviso; `buscar_contexto_financeiro(âncora, pergunta, k)` devolve trechos de `trechos_exemplo.json` com `origem.id_usuario` do âncora (ou `coorte`) e **nunca** de outro usuário; `resumo_mes(âncora, 202512, anomes=202503)` = `resumo_mes__202503.json`; UUID válido ausente de `usuarios.json` → `USUARIO_INEXISTENTE`; UUID malformado → `ENTRADA_INVALIDA`; `simular_objetivo` com `prazo_meses` **e** `aporte_mensal` → `ENTRADA_INVALIDA`, e com nenhum dos dois → `ENTRADA_INVALIDA`; `ate_anomes = 202601` → `ENTRADA_INVALIDA`; controle → `DADOS_INSUFICIENTES` sem dado do âncora; `resumo_mes` com `anomes` > `ate_anomes` → `ENTRADA_INVALIDA`; limites `top_n`/`k` 1–10, `prazo_meses` 1–360, `valor_alvo > 0`, `aporte_mensal > 0`, `pergunta` ≤ 500 caracteres
- [X] T018 [US2] Criar `mcp_server/bussola_mcp/server.py`: `FastMCP("bussola-mcp")`; 8 ferramentas com tipos simples e **validação no código** (R2), ordem: UUID (regex UUID v4) → `ate_anomes` (`202501`–`202512`, mês 01–12) → argumentos da ferramenta → existência do usuário → âncora; corte `ate_anomes == 202512` → golden `__ate_202512`, senão `__ate_202506`, com aviso de mock em `avisos`; `buscar_contexto_financeiro` via `BuscadorFake`; `resumo_mes` via `resumo_mes__<anomes>.json`; erros como envelope `{"erro": {"codigo", "mensagem"}}` (nunca exceção); log JSON (T009) por chamada com `latencia_ms`/`erro_codigo`; `main()` sobe `http` em `0.0.0.0:$PORT` (padrão 8080), caminho `/mcp`
- [X] T019 [US2] Rodar T017 → verde; subir `make mcp` e repetir o exemplo do `quickstart.md` §A (8 ferramentas, golden com aviso de mock, `ENTRADA_INVALIDA`)

**Checkpoint**: US1 + US2 funcionam; ciclos 003/004/006/007 já têm um MCP para consumir.

---

## Phase 5: User Story 3 — Agente hello e pontos de extensão (P1)

**Objetivo**: esqueleto do agente com encadeador, extensões, persistência em memória, conexão MCP e `root_agent`.
**Teste independente**: testes do agente verdes; o `MCPToolset` lista as ferramentas do mock local sem LLM.

### Testes (escrever primeiro)

- [X] T020 [P] [US3] `agent/tests/contrato/test_callbacks.py`: as 4 fases (`before_model`, `after_model`, `before_tool`, `after_tool`) com as assinaturas do ADK 2.10 (R4); ordem crescente; empate mantém a ordem de registro; **função de ordem 10 que retorna valor não nulo impede a de ordem 20**; retorno `None` continua a cadeia; funções síncronas e assíncronas; exceção **propaga**; fase inválida → `ValueError`
- [X] T021 [P] [US3] `agent/tests/contrato/test_extensoes.py`: `carregar_extensoes()` sem os pacotes `governanca`/`acompanhamento` **não levanta**; `ImportError` **dentro** de um pacote presente propaga; `registrar_instrucao` concatena por `ordem` crescente; `registrar_ferramenta(fn, sensivel=True)` aparece em `sensiveis()` (Q-010)
- [X] T022 [P] [US3] `agent/tests/contrato/test_persistencia.py`: `isinstance(RegistroEmMemoria(), RegistroApp)`; `registrar_plano`/`registrar_consentimento`/`registrar_evento` devolvem id (UUID quando vazio) e `obter_plano` recupera; `registrar_acompanhamento` guarda; DDL de `bussola_app.sql` ↔ modelos `Plano`, `Consentimento`, `EventoAuditoria`, `Acompanhamento` (mesmo parser/mapa de tipos do T006)
- [X] T023 [P] [US3] `agent/tests/contrato/test_estado.py`: as 10 chaves de contratos §6; `EstadoJornada` com exatamente `OBJETIVO, ENTENDER, ANTECIPAR, ORIENTAR, AGIR, ACOMPANHAR`; `escrever` rejeita chave desconhecida; `ler` devolve o padrão
- [X] T024 [P] [US3] `agent/tests/contrato/test_mcp_conexao.py`: fixture que sobe o mock (`uv run --frozen --project ../mcp_server python -m bussola_mcp.server`, porta livre, aguarda ficar pronto, encerra no fim) → **o `MCPToolset` conecta e lista as 8 ferramentas sem LLM (AC6)**; `chamar_ferramenta` **força** `id_usuario` e `ate_anomes` do `state` (valores do modelo são ignorados) e devolve o envelope; `state` sem chaves → envelope `ENTRADA_INVALIDA` local
- [X] T025 [P] [US3] `agent/tests/contrato/test_agent_hello.py` (`BUSSOLA_FAKES=TRUE`): `root_agent` importável; os 4 callbacks agregados instalados; toolset presente; instrução em pt-BR não vazia; sem `BUSSOLA_MODEL` e sem `BUSSOLA_FAKES` falha com mensagem que cita `deploy/smoke_modelos.py`

### Implementação

- [X] T026 [P] [US3] `agent/bussola_agent/estado.py`: constantes das chaves, `EstadoJornada` (`StrEnum`), `ler`, `escrever` (contratos §6)
- [X] T027 [P] [US3] `agent/bussola_agent/callbacks.py`: `registrar(fase, funcao, ordem)`, `limpar()` (teste), 4 callbacks agregados assíncronos (R4)
- [X] T028 [P] [US3] `agent/bussola_agent/extensoes.py`: `registrar_ferramenta(fn, sensivel=False)`, `registrar_instrucao(ordem, texto)`, `ferramentas()`, `instrucoes()`, `sensiveis()`, `carregar_extensoes()` (ignora **só** a ausência de `bussola_agent.governanca` e `bussola_agent.acompanhamento`); constantes documentadas das faixas de ordem de instrução reservadas (004: 0–49, 005: 50–69, 006: 70–89), sem enforcement
- [X] T029 [US3] `agent/bussola_agent/persistencia.py`: `Plano`, `Consentimento`, `EventoAuditoria`, `Acompanhamento` (campos = colunas de `bussola_app.sql`), `RegistroApp` (`Protocol`, `runtime_checkable`, 5 métodos de contratos §6), `RegistroEmMemoria`; campos de id com padrão `""` (tipo `str`, coluna `NOT NULL`) e o registro gera UUID quando o id vem vazio
- [X] T030 [US3] `agent/bussola_agent/mcp_conexao.py`: `criar_toolset()` (`MCPToolset` + `StreamableHTTPConnectionParams(url=MCP_URL)`; com `MCP_USE_OIDC=TRUE`, `header_provider` com ID token de `audience` = URL base do MCP, R3) e `async chamar_ferramenta(nome, args, state) -> dict`
- [X] T031 [US3] `agent/bussola_agent/agent.py` e `agent/bussola_agent/__init__.py` (`from . import agent`): `root_agent` (`LlmAgent`) com o toolset, `ferramentas()`, instrução mínima pt-BR + `instrucoes()`, os 4 callbacks agregados e `carregar_extensoes()`; modelo de `BUSSOLA_MODEL` (R7); **sem lógica de negócio**; confirmar com `adk web --help` as flags usadas no `make agent` e no `agent/Dockerfile`
- [X] T032 [US3] Rodar T020–T025 → verdes

**Checkpoint**: US1–US3 completas; AC6, AC8, AC9, AC10 cobertos.

---

## Phase 6: User Story 4 — Convenções, governança e comandos (P2)

**Teste independente**: ler `CLAUDE.md`, rodar cada target do `Makefile`, conferir a constituição.

- [X] T033 [P] [US4] Criar `CLAUDE.md` na raiz: comandos `make`, modo `BUSSOLA_FAKES`, onde ficam os contratos (`docs/ciclos/contratos.md`, `contracts/`), tabela de propriedade (link para contratos §1), proibição de SQL concatenado e de logar prompts ou segredos, fluxo de PR; pré-requisito `uv python install 3.12`
- [X] T034 [P] [US4] `mcp_server/tests/contrato/test_politicas_repo.py` (as verificações "sem segredos" e "sem SQL concatenado" também respondem pelo `test_sem_segredos` citado no plano): **artefatos do 000 existem** (lista de contratos §1 marcada 000: `CLAUDE.md`, `Makefile`, `.specify/`, `contracts/bigquery/{bussola_dados,bussola_rag,bussola_app}.sql`, `contracts/env.example`, `contracts/fixtures/`, `data/scripts/{aplicar_ddl,gerar_fixtures}.py`, `mcp_server/{pyproject.toml,Dockerfile}`, `mcp_server/bussola_mcp/{contratos,logging_json,server}.py`, `mcp_server/bussola_mcp/dominio/{interfaces,fakes}.py`, `agent/{pyproject.toml,Dockerfile}`, `agent/bussola_agent/{estado,callbacks,persistencia,mcp_conexao,extensoes,logging_json,agent}.py`, `deploy/`, `mcp_server/tests/contrato/`, `agent/tests/contrato/`) e o mapa §1 **não** cita `web/`; **`contracts/env.example`**: contém exatamente as variáveis da tabela de contratos §7 (19; a lista é lida de `docs/ciclos/contratos.md`), `GOOGLE_API_KEY` sem valor; **sem segredos** (arquivos versionados **e novos ainda não rastreados**, via `git ls-files --cached --others --exclude-standard`, sem `AIza[0-9A-Za-z_-]{35}`, `-----BEGIN (RSA |EC )?PRIVATE KEY-----`, `ya29\.`; `gemini-api-key` só por nome) e **sem SQL concatenado** (nenhum f-string/concatenação iniciando `SELECT|INSERT|UPDATE|DELETE|MERGE` nos `.py` de `mcp_server`, `agent`, `data`, `deploy`)
- [X] T035 [P] [US4] `mcp_server/tests/contrato/test_bq_datasets.py` com `@pytest.mark.bq` (verifica se os 4 datasets existem; **pula** sem credenciais ADC) para o `make test-bq` não terminar em "nenhum teste coletado"
- [X] T036 [US4] Verificar a constituição contra `spec.md` FR-001: os 7 princípios e as 3 seções presentes, sem placeholders (checagem manual documentada em `traceability.md`)

**Checkpoint**: US4 completa.

---

## Phase 7: User Story 5 — Plataforma GCP validada e pipeline (P2)

**Objetivo**: entregar os scripts e testar offline o que dá; a execução ao vivo é pendência (Phase 10).

- [X] T037 [P] [US5] Testes (falham primeiro) em `mcp_server/tests/contrato/`: `test_aplicar_ddl.py` (`--dry-run` imprime 4 `CREATE SCHEMA` e todas as tabelas, **todas as instruções com `IF NOT EXISTS`**, `bussola_app` aplicado a `bussola_app` e `bussola_app_dev`, sem abrir conexão); `test_smoke_modelos.py` (funções puras: escolhe o **primeiro** candidato que responde na ordem dada, reescreve `BUSSOLA_MODEL=`/`EMBEDDING_MODEL=` em `env.example`, **nunca imprime** a chave); `test_deploy_scripts.py` (`bash -n` nos 3 `.sh`; `iam_datasets.sh` não tem flag que dispense a confirmação; `DRY_RUN=1` imprime os comandos sem executar)
- [X] T038 [US5] `data/scripts/aplicar_ddl.py`: lê `contracts/bigquery/*.sql`, substitui `{project}` (`GOOGLE_CLOUD_PROJECT`, padrão `batalha-time-07-lkbv`) e `{dataset}`, cria `bussola_dados`, `bussola_rag`, `bussola_app`, `bussola_app_dev` (`us-central1`) de forma idempotente; `--dry-run`
- [X] T039 [US5] `deploy/smoke_modelos.py`: tenta `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.5-flash` (nessa ordem) e os candidatos de embedding (R8) via Vertex (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`), mede latência e dimensão; grava IDs em `contracts/env.example` e o relatório em `specs/000-fundacao-contratos/modelos.md`; se nenhum Flash responder, registra e, com `--fallback-api`, testa via Gemini API lendo a chave por `gcloud secrets versions access` **em memória, sem imprimir**
- [X] T040 [P] [US5] `mcp_server/Dockerfile` e `agent/Dockerfile` (contexto = raiz do repositório, R6): `python:3.12-slim` + `uv` com versão fixada, `uv sync --frozen --no-dev`, `PORT=8080`; MCP copia `mcp_server/bussola_mcp` + `contracts/fixtures` e roda `python -m bussola_mcp.server`; agente copia `agent/` e serve `adk web --host 0.0.0.0 --port $PORT`; se houver daemon Docker, `docker build --platform linux/amd64` das duas imagens (registrar o resultado; sem daemon = pendência)
- [X] T041 [US5] `deploy/build_push.sh <servico>` (`docker buildx build --platform linux/amd64 -f <dir>/Dockerfile`, tag = SHA curto, push para `us-central1-docker.pkg.dev/batalha-time-07-lkbv/agentes/<servico>`) e `deploy/deploy.sh <servico> [--tag cNNN --no-traffic]` (R14: **sempre** `--tag c000 --no-traffic`; só se o `gcloud` recusar a combinação ao **criar** um serviço novo, cria sem `--no-traffic`, com aviso, e o desvio é registrado em `deploy.md`; ambos `--no-allow-unauthenticated`; agente com `--max-instances=1` e `MCP_URL`/`MCP_USE_OIDC=TRUE`; verificação final: sem token → recusado, com `gcloud auth print-identity-token` → responde); `DRY_RUN=1` imprime sem executar
- [X] T042 [US5] `deploy/iam_datasets.sh`: `dataViewer` em `bussola_dados` e `bussola_rag`, `dataEditor` em `bussola_app` e `bussola_app_dev` para `1061873050224-compute@developer.gserviceaccount.com`; imprime o plano e exige **confirmação digitada lida de `/dev/tty`**; **sem** flag `--yes`
- [X] T043 [US5] Criar `specs/000-fundacao-contratos/modelos.md`, `smoke.md` e `deploy.md` como **stubs de pendência** (cabeçalho `STATUS: PENDENTE — não executado (sem gcloud/ADC)` + comando exato a rodar); não registram resultados inventados
- [X] T044 [US5] Rodar T037 → verde

**Checkpoint**: scripts prontos e validados offline.

---

## Phase 8: User Story 6 — Pedidos ao owner e decisão Plano A/B (P3)

- [X] T045 [US6] `specs/000-fundacao-contratos/pedidos-owner.md` (pt-BR, pronto para envio) com os 4 itens do contexto mestre §16: (1) service account de runtime com `aiplatform.user`, `bigquery.jobUser`, `bigquery.dataViewer`, `secretmanager.secretAccessor`, `modelarmor.user`, `logging.logWriter`; (2) template de Model Armor (`bussola-guard`); (3) bucket (`batalha-time-07-lkbv-bussola`) com Storage Object Admin; (4) confirmação de `allUsers` como invoker. Seção de status **"não enviado"** (o agente não envia mensagens; quem envia é a Pessoa B) e **decisão Plano A/B: pendente**, com o caminho do Plano B já preparado (`deploy/iam_datasets.sh`, `gemini-api-key`, `list_rows`)

---

## Phase 9: Polish e validação

- [X] T046 Atualizar `docs/ciclos/contratos.md` no mesmo PR (aditivo; Q-001…Q-004, Q-007, Q-008, Q-010): §8 — entradas fixas dos goldens, comportamento do mock para o controle, `origem` em `usuarios.json`, `buscar_contexto_financeiro` via `BuscadorFake`, `referencia_coorte.json = []`; §6 — `extensoes.sensiveis()`; §2 — `fastmcp` como biblioteca do servidor; marcar as linhas correspondentes de `questoes.md` como resolvidas
- [X] T047 **Quality gates**: `make lint` e `make test` verdes nos dois projetos, `BUSSOLA_FAKES=TRUE`, sem rede (bloqueio de T002/T003 ativo); `make test-bq` termina sem erro (testes pulam)
- [X] T048 **Regressão/quickstart**: executar `quickstart.md` §A e §B e conferir os resultados esperados
- [X] T049 Rastreabilidade: `traceability add` com `plan`/`task`/`test`/`status` para AC1–AC15; exportar para `specs/000-fundacao-contratos/traceability.md` (AC4, AC7, AC11–AC13 marcados **PENDENTE-GCP**; AC15 marcado **PENDENTE-HUMANO**)
- [X] T050 **Cleanup/review**: remover o comentário *Sync Impact Report* de `.specify/memory/constitution.md` (rascunho para revisão, não conteúdo de governança); revisar `git status`/`git diff` (nenhum `.venv`, `__pycache__`, segredo ou arquivo fora dos caminhos do 000); `ruff format` aplicado
- [X] T051 Relatório final do Spec Master (`.spec-master/reports/final-report.md`): status honesto, pendências, texto do **aviso S0** para a Pessoa B ("000 em `main` e `contratos-v1` publicada. Pode abrir as worktrees do 004 e do 007.") — enviado por uma pessoa, não pelo agente

---

## Phase 10: Pendências (execução humana; **não** feitas por este run)

- [ ] T052 [HUMANO-GCP] `make fixtures` contra a base real; conferir os valores de referência do âncora dentro de **1%** (renda ≈ 7.451, gasto ≈ 4.615, sobra ≈ 2.836, aluguel ≈ 1.077, comer fora ≈ 364, assinaturas ≈ 101, juros ≈ 61, saldo mínimo ≈ −2.072, saldo máximo ≈ 49.321); ajustar as regras provisórias (Q-006); PR `contracts:` (AC4)
- [ ] T053 [HUMANO-GCP] `python3 data/scripts/aplicar_ddl.py` **duas vezes**; a 2ª não altera nada (AC11)
- [ ] T054 [HUMANO-GCP] `uv run --project agent python deploy/smoke_modelos.py` → IDs em `contracts/env.example` e `modelos.md` (AC12)
- [ ] T055 [HUMANO-GCP] `deploy/build_push.sh` e `deploy/deploy.sh` para `bussola-mcp` e `bussola-agent`; registrar em `deploy.md` o que funcionou com a SA default (alimenta Plano A/B) (AC13)
- [ ] T056 [HUMANO-GCP] `make agent` local: "qual é o meu perfil financeiro?" → `perfil_financeiro`; registrar em `smoke.md` (AC7)
- [ ] T057 [HUMANO-GCP] `deploy/iam_datasets.sh` (Plano B), **só com confirmação humana**
- [ ] T058 [HUMANO] Pessoa B envia `pedidos-owner.md` ao owner; registrar a decisão Plano A/B (AC14)
- [ ] T059 [HUMANO] Revisão por **≥ 2 pessoas**, merge em `main`, `git tag contratos-v1 && git push origin contratos-v1` (AC15)

---

## Dependências e ordem de execução

- **Phase 1 → Phase 2 → histórias.** Phase 2 bloqueia todas (modelos, DDL, logger).
- **US1** (contratos consumíveis) → **US2** (mock usa fakes, fixtures, modelos) → **US3** (o teste T024 sobe o mock; `persistencia` usa o DDL de `bussola_app`).
- **US4** e **US5** só dependem da Phase 2 (T034 lê o repositório todo → rodar por último dentro da fase); **US6** é independente.
- **Polish** depende de US1–US6. **Phase 10** depende do merge do PR ou de credenciais.
- Dentro de cada história: testes (falhando) → modelos/interfaces → implementação → verde.

### Oportunidades de paralelismo

- Phase 1: T001 ∥ T003 (T002 antes de T004).
- Phase 2: T006 ∥ T007 ∥ T009.
- US1: T010 ∥ T011. US3: T020–T025 juntos; T026 ∥ T027 ∥ T028. US4: T033 ∥ T034 ∥ T035. US5: T037 ∥ T040.
- US3 (agente) pode andar em paralelo com US2 (mock) até o T024, que precisa do T018.

## Cobertura AC → tarefas

| AC | Tarefas | Observação |
|---|---|---|
| AC1 | T033, T036 | constituição e `CLAUDE.md` |
| AC2 | T002–T005, T047 | `make lint`/`make test`, offline, sem rede |
| AC3 | T006–T008, T012, T015, T017, T022 | DDL↔modelos; schema do mock×§5 |
| AC4 | T010, T013, T014, **T052** | offline: sintético; real: pendente |
| AC5 | T017–T019 | mock completo |
| AC6 | T024, T030 | `MCPToolset` × mock, sem LLM |
| AC7 | T031, T043, **T056** | smoke com LLM: pendente |
| AC8 | T020, T027 | |
| AC9 | T021, T028 | |
| AC10 | T022, T029 | |
| AC11 | T037, T038, **T053** | dry-run offline; execução real pendente |
| AC12 | T037, T039, **T054** | idem |
| AC13 | T040, T041, **T055** | build local se houver Docker; deploy pendente |
| AC14 | T045, **T058** | pedidos redigidos; envio humano |
| AC15 | **T059** | humano, após o merge |

## Estratégia de implementação

1. **MVP:** Setup → Foundational → US1 → US2 (contratos + mock: já desbloqueia 003/004/006/007). Validar.
2. US3 (agente/extensões) → US4 → US5 → US6 → Polish.
3. Commits por história (sem push nem PR sem confirmação do usuário). `make lint` e `make test` a cada história.
4. Parar em qualquer checkpoint para validar. Pendências GCP e humanas ficam **explícitas** no relatório final, nunca dadas como cumpridas.
