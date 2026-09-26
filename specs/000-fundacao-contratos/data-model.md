# Data Model — 000 Fundação e contratos

Fonte canônica das colunas e dos schemas: [`docs/ciclos/contratos.md`](../../docs/ciclos/contratos.md) §3, §5, §6.
Este arquivo só fixa **como** o 000 as materializa e as regras de validação. Não duplica as tabelas.

## 1. Tabelas ↔ DDL ↔ modelos

| Dataset | Tabela | DDL (`contracts/bigquery/`) | Modelo (arquivo · classe) | Fixture (`contracts/fixtures/`) |
|---|---|---|---|---|
| `bussola_dados` | `perfil_mensal` | `bussola_dados.sql` | `mcp_server/bussola_mcp/contratos.py` · `PerfilMes` | `bussola_dados/perfil_mensal.json` |
| | `gastos_categoria` | idem | `GastoCategoria` | `bussola_dados/gastos_categoria.json` |
| | `entradas_categoria` | idem | `EntradaCategoria` | `bussola_dados/entradas_categoria.json` |
| | `recorrentes` | idem | `Recorrente` | `bussola_dados/recorrentes.json` |
| | `parcelas` | idem | `Parcela` | `bussola_dados/parcelas.json` |
| | `categorias` | idem | `Categoria` | `bussola_dados/categorias.json` |
| | `referencia_coorte` | idem | `RefCoorte` | `bussola_dados/referencia_coorte.json` (= `[]`, ver R9) |
| `bussola_rag` | `documentos` | `bussola_rag.sql` | `Documento` | — (só `rag/trechos_exemplo.json`, formato `Trecho`) |
| `bussola_app` (e `_dev`) | `planos` | `bussola_app.sql` | `agent/bussola_agent/persistencia.py` · `Plano` | — |
| | `consentimentos` | idem | `Consentimento` | — |
| | `auditoria` | idem | `EventoAuditoria` | — |
| | `acompanhamento` | idem | `Acompanhamento` | — |

**Regra de contrato (teste):** para cada tabela, `{coluna: tipo}` do DDL == `{campo: tipo Python}` do modelo, e `NOT NULL` ↔ campo não opcional (mapa de tipos em `research.md` R11).
Os modelos de `bussola_app` ficam no `agent/` (contratos §1) e são testados lá; os demais, no `mcp_server/`.

## 2. Envelopes e ferramentas (`contratos.py`)

| Entidade | Campos | Regras |
|---|---|---|
| `Periodo` | `inicio: int`, `fim: int` | `AAAAMM`; `inicio ≤ fim` |
| `Fonte` | `ferramenta: str`, `tabelas: list[str]`, `periodo: Periodo` | `tabelas` só `dataset.tabela` (nunca SQL, projeto ou credencial) |
| `Erro` | `codigo: CodigoErro`, `mensagem: str` | resultado da ferramenta, não exceção |
| `Resposta` | `dados: dict`, `fonte: Fonte`, `avisos: list[str] = []` | envelope de sucesso |
| `RespostaErro` | `erro: Erro` | envelope de erro |
| `CodigoErro` (`StrEnum`) | `USUARIO_INEXISTENTE`, `ENTRADA_INVALIDA`, `PRAZO_IMPLAUSIVEL`, `DADOS_INSUFICIENTES`, `INDISPONIVEL` | os únicos códigos do MCP; `CONSENTIMENTO_NECESSARIO`, `SEM_PLANO_ATIVO`, `FIM_DO_REPLAY` são **locais do agente** |
| `Trecho` | `doc_id, tipo, anomes, texto, score, origem{id_usuario, anomes, categoria}` | formato de `buscar_contexto_financeiro` |
| Entrada por ferramenta | `EntradaPerfilFinanceiro` … (uma por ferramenta de §5) | campos comuns `id_usuario: str`, `ate_anomes: int` + adicionais de §5 |
| `dados` por ferramenta | `DadosPerfilFinanceiro`, `DadosCapacidadePoupanca`, `DadosOportunidadesCorte`, `DadosDividasParcelas`, `DadosSimularObjetivo`, `DadosCompararCenarios`, `DadosBuscarContexto`, `DadosResumoMes`, `DadosReferenciaCoorte` | espelham a coluna `dados` de §5; `DadosReferenciaCoorte` existe, mas o mock não registra a ferramenta (P1) |

**Validação de entrada (no código, não no schema — R2):**

| Campo | Regra | Erro |
|---|---|---|
| `id_usuario` | UUID v4 (regex) | `ENTRADA_INVALIDA` |
| `ate_anomes`, `anomes` | inteiro `202501…202512` (mês 01–12); `anomes ≤ ate_anomes` em `resumo_mes` | `ENTRADA_INVALIDA` |
| `top_n`, `k` | 1–10 | `ENTRADA_INVALIDA` |
| `valor_alvo` | `> 0` | `ENTRADA_INVALIDA` |
| `prazo_meses` | 1–360 | `ENTRADA_INVALIDA` |
| `aporte_mensal` | `> 0` | `ENTRADA_INVALIDA` |
| `simular_objetivo` | **exatamente um** entre `prazo_meses` e `aporte_mensal` | `ENTRADA_INVALIDA` |
| `pergunta` | ≤ 500 caracteres | `ENTRADA_INVALIDA` |
| usuário | UUID válido ausente de `usuarios.json` → `USUARIO_INEXISTENTE`; conhecido mas não âncora → `DADOS_INSUFICIENTES` | — |

Ordem de validação do mock: UUID → `ate_anomes` → argumentos da ferramenta → existência do usuário → âncora.

## 3. Fixtures (`contracts/fixtures/`)

```text
usuarios.json                          [{id_usuario, papel: "ancora"|"controle", origem: "base_real"|"sintetico_teste"}]
bussola_dados/<tabela>.json            linhas do §3 para os 2 usuários, 12 meses (202501–202512)
ferramentas/_entradas.json             entradas fixas de cada golden (R10)
ferramentas/<ferramenta>__ate_202506.json    envelope esperado (Resposta) — 7 P0 menos buscar_contexto
ferramentas/<ferramenta>__ate_202512.json
ferramentas/resumo_mes__<AAAAMM>.json  12 arquivos (202501–202512), âncora
rag/trechos_exemplo.json               lista de Trecho (âncora + 1 de `coorte`)
```

Goldens: 6 P0 (`perfil_financeiro`, `capacidade_poupanca`, `oportunidades_corte`, `dividas_e_parcelas`, `simular_objetivo`, `comparar_cenarios`) × 2 cortes = 12 arquivos; `buscar_contexto_financeiro` responde via `BuscadorFake` (Q-003).
`origem` em `usuarios.json` é campo novo opcional (Q-004).

## 4. Estado da sessão e registros do agente

| Entidade | Arquivo | Conteúdo |
|---|---|---|
| Chaves de `session.state` | `estado.py` | constantes (`ID_USUARIO`, `ATE_ANOMES`, `ESTADO_JORNADA`, `OBJETIVO`, `CENARIOS`, `CENARIO_ESCOLHIDO`, `ULTIMAS_FONTES`, `CONSENTIMENTOS`, `PLANO_ID`, `ACOMPANHAMENTO`) com os nomes de contratos §6; `EstadoJornada` (`StrEnum`: `OBJETIVO, ENTENDER, ANTECIPAR, ORIENTAR, AGIR, ACOMPANHAR`); `ler(state, chave, padrao=None)`, `escrever(state, chave, valor)` (rejeita chave desconhecida) |
| Registro de callbacks | `callbacks.py` | `dict[fase → list[(ordem, seq, função)]]`; `FASES = (before_model, after_model, before_tool, after_tool)`; `limpar()` só para teste |
| Registro de extensões | `extensoes.py` | ferramentas (`list[Callable]`), nomes sensíveis (`set[str]`), instruções (`list[(ordem, texto)]`); faixas 004: 0–49, 005: 50–69, 006: 70–89 |
| `RegistroApp` | `persistencia.py` | `Protocol` (`runtime_checkable`) com os 5 métodos de contratos §6 |
| `RegistroEmMemoria` | `persistencia.py` | dicts em memória; gera UUID quando o id do registro vem vazio; `registrar_*` devolve o id |

### Transições/regras

- **Callbacks:** ordem crescente; empate mantém a ordem de registro; primeiro retorno `≠ None` interrompe; exceção propaga.
- **Extensões:** `carregar_extensoes()` ignora **apenas** a ausência do pacote (`governanca`, `acompanhamento`); `ImportError` de dentro de um pacote presente propaga.
- **Mock:** golden por corte (`ate_anomes == 202512 → __ate_202512`, senão `__ate_202506`) com aviso de mock acrescentado a `avisos`; nunca devolve dado do âncora a outro usuário.
