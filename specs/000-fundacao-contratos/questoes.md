# Questões, divergências e decisões — ciclo 000

Registro exigido pelo ciclo §1.5 (divergência → aqui; o contrato é corrigido no **mesmo PR**, porque o 000 é dono
do contrato até o merge). Status: `ABERTA` (a corrigir no PR), `RESOLVIDA`, `PENDENTE` (externa).

## Lacunas em `docs/ciclos/contratos.md`

| # | Onde | Lacuna / divergência | Decisão | Status |
|---|---|---|---|---|
| Q-001 | §8 (goldens) | Um golden por ferramenta/corte, mas as ferramentas P0 têm argumentos livres (`top_n`, `valor_alvo`, `prazo_meses`, `aporte_mensal`, `pergunta`, `k`) e §8 não diz quais entradas geram o golden | O gerador fixa e **documenta** as entradas junto de cada golden; o mock valida os argumentos e sempre devolve o golden do corte. Acrescentar a regra em §8 (aditivo) | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-002 | §8 (mock) | Só há golden do âncora; o mock não diz o que devolver ao usuário de controle | `DADOS_INSUFICIENTES`, sem dado do âncora. Acrescentar em §8 | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-003 | §8 (`buscar_contexto_financeiro`) | §8 pede golden de "cada ferramenta P0", mas também diz que `rag/trechos_exemplo.json` alimenta o buscador fake | `buscar_contexto_financeiro` responde via `BuscadorFake` sobre `trechos_exemplo.json` (sem golden separado). Esclarecer em §8 | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-004 | §8 (`usuarios.json`) | Não há campo para marcar a origem das fixtures (reais × sintéticas de teste) | Acrescentar o campo `origem` (`base_real` \| `sintetico_teste`) em §8; campo novo opcional, portanto aditivo | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-006 | §3 / ciclo §3.4 (regras das tabelas) | Contratos não definem como derivar `juros`, `recorrentes` e `categorias` (flag `discricionaria`, `corte_max_pct`) a partir do extrato, e os nomes reais das categorias são desconhecidos offline | Regras **provisórias** no gerador (research R9): `juros` = saídas cuja micro contém "juros"; recorrente = `descr_norm` em ≥ 3 meses; `categorias` por lista configurável de palavras. O 001 é o dono das regras reais; ajustar na 1ª execução com credenciais | ABERTA (provisório; 001 substitui) |
| Q-007 | §8 (`referencia_coorte.json`) | "Linhas das tabelas do §3 para os 2 usuários" não faz sentido para `referencia_coorte` (agregado da população) | `referencia_coorte.json` = `[]`; o mock não registra a ferramenta (P1) | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-008 | §2/ciclo §3.2 (`mcp`/FastMCP) | `mcp` 2.x renomeou `FastMCP` → `MCPServer`; o AC5 cita `fastmcp.Client` | Servidor com o pacote `fastmcp` (>=4,<5) (research R1, ADR-1) | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-009 | Ciclo §3.4 ("SQL de referência") | Agregar em SQL exigiria uma 2ª implementação para o modo sintético | SQL só busca as linhas brutas dos 2 usuários; agregação única em Python (research R9, ADR-2) | RESOLVIDA (desvio documentado no plano) |
| Q-010 | §6 (`extensoes.py`) | `registrar_ferramenta(fn, sensivel)` guarda um flag que nenhuma função lê; o 005 precisa dele | Acrescentar `sensiveis() -> set[str]` (nomes das ferramentas sensíveis); aditivo | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-011 | §5 (`simular_objetivo.modo`) | `modo ("prazo" \| "aporte")` não diz se é a entrada ou a saída | `modo` = a **entrada** informada (`"prazo"`: veio `prazo_meses`, o aporte é calculado). Registrado em §5 | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-012 | §6 (callbacks) | O contrato não diz com que argumentos as funções registradas são chamadas; o ADK 2.10 chama **por nome** (`callback_context`, `llm_request`, `llm_response`, `tool`, `args`, `tool_context`, `tool_response`) | Registrado em §6, com o mesmo nome de parâmetros do ADK; exceção propaga | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-013 | §5 (validação) | Tipos simples errados são recusados pelo FastMCP como erro de protocolo, antes da ferramenta; as faixas viram `ENTRADA_INVALIDA` | Registrado em §5 (onde cada validação acontece e a ordem) | RESOLVIDA (`contratos.md` atualizado neste PR) |
| Q-014 | Ciclo §3.5 / 007 (`adk web`) | O `adk web` **não tem autenticação** (aviso do próprio CLI) e não falha no start sem `BUSSOLA_MODEL`; expor o agente com `allUsers` expõe a UI | Os dois serviços saem privados; o `deploy.sh` do agente aborta sem `BUSSOLA_MODEL`. Tornar público é decisão do 007 (pedido 4 ao owner) | PENDENTE (decisão do 007) |
| Q-005 | Blueprint §5 e mestre §10 F1 × contratos §3 | Nomes/colunas diferentes (`recorrentes.valor_medio/meses_presentes`, `parcelas_dividas`, view `saldo`, `perfil_mensal` sem `saldo_minimo/maximo`, `planos` sem `ate_anomes`) | Vale contratos §3 (o cabeçalho de contratos já declara a precedência). Sem alteração | RESOLVIDA |

## Decisões do clarify (2026-09-26)

| # | Pergunta | Decisão | Origem |
|---|---|---|---|
| D-001 | Como tratar o que exige GCP ao vivo sem `gcloud`/ADC/extrato? | **Offline agora, GCP depois**: scripts + testes offline (extrato sintético só de teste); fixtures commitadas rotuladas provisórias sintéticas; AC4, AC7, AC11–AC13 = pendência declarada | Usuário |
| D-002 | Canal da demo (Q4)? | **ADK Web UI**: sem `web/` nem ponto de entrada de front neste PR; front próprio depois por PR `contracts:` aditivo | Usuário |
| D-003 | Mock × argumentos livres | Valida e devolve o golden do corte | `SAFE_DEFAULT` (contratos §8) |
| D-004 | `make lint` | `ruff check` + `ruff format --check` nos dois projetos | `SAFE_DEFAULT` (INFERRED) |
| D-005 | Python 3.12 ausente no sistema (3.14.7) | `uv` provisiona o 3.12 (`requires-python` do projeto) | `SAFE_DEFAULT` |

## Pendências externas

| # | Item | Dono | Status |
|---|---|---|---|
| P-001 | Resposta do owner aos pedidos do mestre §16 (define Plano A/B) — Q7 | Pessoa B envia; owner responde | PENDENTE |
| P-002 | Fixtures reais + checagem de 1% do âncora (AC4) | integrante com `gcloud`/ADC | PENDENTE |
| P-003 | `aplicar_ddl.py`, `smoke_modelos.py`, build/push/deploy e smoke do agente com LLM (AC7, AC11–AC13) | integrante com `gcloud`/ADC | PENDENTE |
| P-004 | Execução de `deploy/iam_datasets.sh` (exige confirmação humana) | integrante | PENDENTE |
| P-005 | Revisão por ≥ 2 pessoas, merge e tag `contratos-v1` | time | PENDENTE |
