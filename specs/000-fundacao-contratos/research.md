# Research — 000 Fundação e contratos

Fase 0 do `plan`. Cada decisão tem alternativas e a evidência (API inspecionada no ambiente de pesquisa:
Python 3.12.12 via `uv`, `google-adk 2.10.0`, `fastmcp 4.0.10`, `mcp 2.2.0`, `google-genai 2.25.0`,
`pydantic 2.13.5`, `pytest 9.1.1`, `ruff 0.16.9`). Marcador **ADR** = decisão que o perfil XL manda registrar.

## R1 — Biblioteca do servidor MCP e do cliente de teste  · **ADR**

- **Decisão:** dependência `fastmcp` (>=4,<5) no `mcp_server/`; servidor `fastmcp.FastMCP`; testes com `fastmcp.Client(mcp)` em memória.
- **Evidência:** no `mcp` 2.x o `FastMCP` foi renomeado para `MCPServer` (`from mcp.server.fastmcp` falha com aviso de migração);
  o pacote `fastmcp` mantém `FastMCP` e `Client`, e o AC5 cita `fastmcp.Client`. `Client(mcp)` roda o servidor em memória (sem rede, sem porta), o que serve o AC2.
- **Alternativas:** `mcp` oficial 2.x com `MCPServer` (API nova, não citada nos contratos; teria de reescrever o AC5); `mcp<2` (fixa API antiga, dívida imediata).
- **Consequência:** o ciclo §3.2 diz "`mcp`/FastMCP"; fica `fastmcp` (que traz `mcp`). Registrar em `questoes.md` (Q-008).

## R2 — Validação de entrada e o envelope `ENTRADA_INVALIDA`

- **Evidência:** o FastMCP valida os **tipos** dos argumentos antes de chamar a função e devolve erro de protocolo (`ToolError`), por exemplo `ate_anomes="abc"`; restrições `Field(ge/le)` também viram erro de protocolo, não envelope.
- **Decisão:** a assinatura das ferramentas só usa tipos simples (`str`, `int`, `float`, `bool`) com os defaults de contratos §5; **todas as faixas e regras** (UUID, `202501–202512`, `top_n` 1–10, `k` 1–10, `prazo_meses` 1–360, `valor_alvo > 0`, `pergunta ≤ 500`, prazo XOR aporte) ficam no código e devolvem o envelope `{"erro": {...}}`. Tipo errado (ex.: texto onde vai inteiro) continua sendo recusado pelo protocolo.
- **Consequência:** o teste de schema compara nomes, obrigatoriedade, tipo simples e default; as faixas são testadas por chamada.

## R3 — Cliente MCP no agente e autenticação OIDC

- **Evidência:** `google.adk.tools.mcp_tool.McpToolset(connection_params=StreamableHTTPConnectionParams(url, headers, timeout, …), tool_filter, tool_name_prefix, header_provider=…)`; `MCPToolset` é alias. `header_provider(ReadonlyContext) -> dict[str,str]` (síncrono ou assíncrono) permite gerar o header por chamada.
- **Decisão:** com `MCP_USE_OIDC=TRUE`, usar `header_provider` que devolve `Authorization: Bearer <ID token>` obtido por `google.oauth2.id_token.fetch_id_token(Request(), audience)` (audience = URL base do MCP), com cache curto (o token expira em ~1 h). Sem OIDC, sem header.
- **Limite conhecido (verificado no docstring de `fetch_id_token`, google-auth 2.58.1):** só obtém o token via `GOOGLE_APPLICATION_CREDENTIALS` (service account) ou metadata server (Cloud Run); sem isso levanta `DefaultCredentialsError`. ADC de usuário não é listado. Localmente, `MCP_USE_OIDC=FALSE`. A chamada de um integrante ao MCP privado usa `gcloud auth print-identity-token` (no `deploy.sh`), e não o Python.
- **`chamar_ferramenta`:** usa o cliente do SDK `mcp` (streamable HTTP), declarado como dependência explícita do `agent/` (hoje só transitivo via `google-adk`); força `id_usuario` e `ate_anomes` a partir do `state` e devolve o envelope do servidor. Falta de chave no `state` → envelope de erro local `ENTRADA_INVALIDA`.

## R4 — Assinaturas de callbacks do ADK 2.10  · base do encadeador

- **Evidência (código do ADK 2.10, `flows/llm_flows/core/_finalizer.py` e `tools/_caller.py`):** os callbacks são chamados **por nome de argumento**: `before_model(callback_context, llm_request)`, `after_model(callback_context, llm_response)`, `before_tool(tool, args, tool_context)`, `after_tool(tool, args, tool_context, tool_response)`. `callback_context`/`tool_context` são `Context` (com `.state`). Cada callback pode ser função síncrona ou assíncrona; o `LlmAgent` aceita um callable **ou** lista.
- **Decisão:** o encadeador guarda `(ordem, seq, função)` por fase, ordena por `(ordem, seq)` e expõe **um** callable assíncrono agregado por fase, com **esses mesmos nomes de parâmetro** (o `agent.py` instala só os 4). As funções registradas são chamadas **por nome**, com os mesmos argumentos (por isso ganham o mesmo contrato do ADK). Cada função pode ser síncrona ou assíncrona (`inspect.isawaitable`). O primeiro retorno não `None` interrompe. Exceção dentro de uma função **propaga** (não é engolida). Registrar em `questoes.md` (Q-012): contratos §6 passa a dizer que as funções registradas recebem os argumentos do ADK por nome.
- **Alternativa rejeitada:** passar a lista ordenada ao ADK — a semântica de parada depende do ADK e não permite o registro tardio por outros pacotes.

## R5 — Layout dos projetos e empacotamento

- **Decisão:** projetos `uv` **sem pacote instalável** (`[tool.uv] package = false`), layout plano (`bussola_mcp/`, `bussola_agent/` na raiz do projeto, `tests/` ao lado), `pytest` com `pythonpath = ["."]`. Ruff com **um** `ruff.toml` na raiz do repositório (line-length 100, alvo py312), rodando em cada projeto (`ruff check` e `ruff format --check`).
- **Alternativas:** layout `src/` + build backend (mais arquivos e config, sem ganho para um serviço); `pyproject` por projeto com `[tool.ruff]` duplicado.
- **`requires-python`:** `>=3.12,<3.13`. Python 3.12 ausente no sistema (tem 3.14): `uv python install 3.12` (feito na pesquisa).

## R6 — Contexto de build dos Dockerfiles

- **Evidência:** o mock precisa das fixtures (`contracts/fixtures/`), que ficam **fora** de `mcp_server/`.
- **Decisão:** contexto de build = raiz do repositório (`docker buildx build -f mcp_server/Dockerfile .`), com `.dockerignore` na raiz; a imagem copia `mcp_server/bussola_mcp` e `contracts/fixtures`. O `agent/Dockerfile` copia só `agent/`. `build_push.sh` fixa o contexto e `--platform linux/amd64`. Imagem base `python:3.12-slim`; `uv` copiado de `ghcr.io/astral-sh/uv` com versão fixada.
- **Risco:** `ghcr.io` bloqueado na rede do time → alternativa `pip install uv` na imagem (registrar se ocorrer).

## R7 — Agente servido pela ADK Web UI

- **Decisão:** `bussola_agent/__init__.py` faz `from . import agent` e `agent.py` define `root_agent` (convenção do `adk web`). Container: `adk web --host 0.0.0.0 --port $PORT` sobre a pasta que contém `bussola_agent/`. Confirmar o comando e as flags com `adk web --help` na implementação (CLI muda entre versões).
- **Modelo:** `BUSSOLA_MODEL` vem do ambiente. Sem ele e sem `BUSSOLA_FAKES=TRUE`, `agent.py` falha com mensagem que aponta para `deploy/smoke_modelos.py` (não se inventa ID de modelo). Com `BUSSOLA_FAKES=TRUE` (testes), usa um nome de teste que nunca é enviado a um serviço.

## R8 — IDs de modelos a validar (não fixar)

- **Decisão:** `smoke_modelos.py` tenta, em ordem, `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.5-flash` (nomes derivados do Model Garden do mestre §5, **sem confirmação**) e, para embedding, `gemini-embedding-001` e `text-embedding-005`; ambas as listas são substituíveis por flag. Até rodar com credenciais, `contracts/env.example` deixa `BUSSOLA_MODEL=` e `EMBEDDING_MODEL=` **vazios**, com comentário dos candidatos. **UNRESOLVED** até o smoke.

## R9 — Geração das fixtures: uma só agregação, em Python  · **ADR**

- **Decisão:** o gerador busca do BigQuery apenas as **linhas brutas** dos 2 usuários (`SELECT … WHERE id_usuario IN UNNEST(@ids)`, parametrizado, somente leitura) e agrega em Python (`agregar_extrato(linhas) -> tabelas`). O modo `--sintetico` alimenta a **mesma** função com um extrato sintético mínimo e determinístico. Uma única implementação de agregação, testável offline.
- **Desvio do texto do ciclo (§3.4 "SQL de referência"):** o SQL é só a busca das linhas; a agregação não é SQL. Justificativa: ~2 usuários × 12 meses cabem em memória, e duas implementações (SQL + Python) divergiriam sem nada para detectar. O 001 faz o SQL de produção. Registrar em `questoes.md` (Q-009).
- **Regras provisórias** (dono real: 001, aparecem como tal nos avisos do gerador e em `questoes.md`): (a) `juros` = soma de `vlr` das saídas cuja microcategoria contém "juros"; (b) `recorrentes` = `descr_norm` (minúsculas, sem dígitos) presente em ≥ 3 meses; (c) `categorias` = pares (macro, micro) observados; `discricionaria=True` e `corte_max_pct=0.30` se o nome contiver uma palavra de uma lista configurável, senão `False` e `0.0`; (d) `referencia_coorte.json` = `[]` (a coorte precisa da população inteira, que o gerador não lê). **Os nomes reais das categorias são desconhecidos offline**: a regra (a) e a lista de (c) provavelmente precisarão de ajuste na 1ª execução com credenciais (é exatamente o que o SC-006 vai revelar).
- **Alternativas:** SQL de agregação no BigQuery (fiel ao texto, mas sem teste offline e duplicaria no 001); fixtures escritas à mão (números inventados: rejeitado).

## R10 — Referência dos goldens

- **Decisão:** implementação de referência mínima no próprio gerador, sobre as linhas já agregadas (funções puras): médias e mediana sobre os meses `≤ ate_anomes`; desvio padrão **populacional** (`statistics.pstdev`); `oportunidades_corte` = `media_mensal × corte_max_pct` sobre categorias discricionárias; `simular_objetivo` no modo "prazo" (`aporte = valor_alvo / prazo_meses`, rendimento 0, saldo inicial 0); `comparar_cenarios` com `RegrasCenario` de contratos §4 (0,40/0,60/0,80 da sobra mediana). Arredondamento a 2 casas. Todo golden é validado pelos modelos Pydantic antes de gravar.
- **Entradas fixas** (documentadas em `contracts/fixtures/ferramentas/_entradas.json`; são só entradas de exemplo): `top_n=5`; `valor_alvo=60000.0` e `prazo_meses=36`; `pergunta="quanto gasto com comer fora?"`, `k=5`.
- **Cortes:** `__ate_202506` e `__ate_202512`; `resumo_mes__AAAAMM` de 202501 a 202512.

## R11 — DDL e placeholders

- **Decisão:** `contracts/bigquery/*.sql` usam `{project}` e `{dataset}`; `aplicar_ddl.py` substitui (projeto de `GOOGLE_CLOUD_PROJECT`, padrão `batalha-time-07-lkbv`) e aplica `bussola_app.sql` duas vezes (`bussola_app` e `bussola_app_dev`). Todas as instruções usam `IF NOT EXISTS`; `CREATE SCHEMA … OPTIONS(location="us-central1")`. Colunas `NOT NULL` exceto as marcadas `NULL` em contratos §3. `--dry-run` imprime as instruções sem conectar.
- **Mapa de tipos** (usado pelo teste de contrato): `STRING→str`, `INT64→int`, `FLOAT64→float`, `BOOL→bool`, `TIMESTAMP→datetime`, `JSON→dict`, `ARRAY<FLOAT64>→list[float]`; coluna nula ↔ `X | None`.

## R12 — Testes que dependem de GCP

- **Decisão:** marcador `bq` registrado; um teste `@pytest.mark.bq` (datasets existem, pula sem credenciais) em `mcp_server`, para `make test-bq` não terminar com "nenhum teste coletado" (código 5). O Makefile tolera o código 5 nos dois projetos.
- **Nada** no `make test` padrão toca rede, exceto o teste do AC6, que sobe o mock em `localhost` (porta livre) num subprocesso.

## R13 — Segredos e verificação

- **Decisão:** teste `test_sem_segredos` varre os arquivos versionados atrás de padrões de chave (`AIza[0-9A-Za-z_-]{35}`, `-----BEGIN (RSA |EC )?PRIVATE KEY-----`, `ya29\.` de token OAuth) e falha se achar. `gemini-api-key` só aparece por **nome** (Secret Manager), nunca por valor. O Plano B lê o valor com `gcloud secrets versions access` em memória, sem imprimir.

## R14 — Deploy do 000 e a regra `--no-traffic`

- **Não verificado:** não há `gcloud` neste ambiente. Suspeita (conhecimento prévio, **sem confirmação**): o Cloud Run pode exigir que a **primeira** revisão de um serviço novo receba tráfego, o que recusaria `--no-traffic` na criação.
- **Decisão:** `deploy.sh` **sempre tenta** `--tag c000 --no-traffic` (constituição VII), inclusive na criação. Só se o `gcloud` recusar essa combinação num serviço novo, cria o serviço sem `--no-traffic`, com aviso, e o desvio é registrado em `deploy.md`. Não se assume o desvio de antemão. Ambos os serviços saem `--no-allow-unauthenticated` (tornar o agente público é decisão do 007/`allUsers`). O 000 não move tráfego depois da criação. Ver Complexity Tracking do `plan.md`.

## R15 — Versões e lock

- **Decisão:** faixas compatíveis no `pyproject` (`google-adk>=2.10,<3`, `fastmcp>=4,<5`, `google-genai>=2,<3`, `pydantic>=2.13,<3`, `google-cloud-bigquery>=3.45,<4`, `numpy>=2.5,<3`, `pytest>=9,<10`, `pytest-asyncio>=1.4,<2`, `ruff>=0.16,<0.17`) e `uv.lock` versionado; `uv sync --frozen` nas imagens. As versões refletem o que a pesquisa instalou hoje; o 001–007 acrescentam dependências (contratos §1).
