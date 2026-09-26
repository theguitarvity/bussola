# Feature Specification: Fundação e contratos

**Feature Branch**: `000-fundacao-contratos`

**Created**: 2026-09-26

**Status**: Draft

**Input**: User description: "Criar o esqueleto do repositório e materializar os contratos v1 da Bússola em código (DDL, modelos, interfaces, fakes, fixtures, MCP mock, agente hello, encadeador de callbacks, extensões, persistência em memória, conexão MCP), validar a plataforma GCP (modelos, datasets, pipeline build → push → Cloud Run) e redigir os pedidos ao owner, para que os ciclos 001–007 rodem em paralelo sem depender uns dos outros." Fonte normativa: `docs/ciclos/000-fundacao-contratos.md` e `docs/ciclos/contratos.md`.

## Clarifications

### Session 2026-09-26

- Q: Como tratar o que exige GCP ao vivo se o ambiente não tem `gcloud`, ADC nem o extrato? → A: **Offline agora, GCP depois** (decisão do usuário). Entregam-se scripts e testes offline com extrato sintético mínimo só para teste; as fixtures commitadas são rotuladas como provisórias sintéticas e substituídas depois por PR `contracts:`; AC4, AC7 e AC11–AC13 ficam como pendência declarada para quem tem `gcloud`/ADC.
- Q: Qual o canal da demo (Q4 do contexto mestre)? → A: **ADK Web UI** (decisão do usuário). Sem alteração no mapa de contratos §1 e sem `web/` neste PR; um front próprio depois é um acréscimo aditivo por PR `contracts:`.
- Q: O mock devolve o golden independentemente dos argumentos livres de `simular_objetivo`, `comparar_cenarios` e `oportunidades_corte`? → A: Sim; valida os argumentos e devolve o golden do corte (`SAFE_DEFAULT`, de acordo com contratos §8). `buscar_contexto_financeiro` responde a partir de `rag/trechos_exemplo.json` (`RESOLVABLE_FROM_CONTEXT`, contratos §8).
- Q: O que o mock devolve para um usuário conhecido que não é o âncora (o controle)? → A: `DADOS_INSUFICIENTES`, sem devolver dado do âncora (`SAFE_DEFAULT`; contratos §8 só prevê golden do âncora).
- Q: Quais entradas fixas geram cada golden? → A: contratos §8 não as especifica (lacuna de contrato). O gerador MUST documentar as entradas usadas junto de cada golden; a lacuna é registrada em `questoes.md` e corrigida em contratos §8 no mesmo PR (`RESOLVABLE_FROM_CONTEXT`, ciclo §1.5).

## User Scenarios & Testing *(mandatory)*

<!--
  Os "usuários" desta feature são as pessoas do time que executam os demais ciclos (001–007),
  quem revisa o PR e quem opera a plataforma GCP. Não há cliente final: o produto (jornada do
  cliente) é construído pelos ciclos seguintes.
-->

### User Story 1 - Ciclo consumidor trabalha sobre contratos congelados (Priority: P1)

Uma pessoa que executa um ciclo consumidor (001, 003, 004, 005, 006 ou 007) abre a sua worktree a partir de `main` e encontra os contratos v1 materializados: esquema das tabelas, modelos de entrada e saída das ferramentas, interfaces de domínio, implementações fake sobre fixtures, chaves do estado de sessão e convenções. Ela desenvolve e testa o seu ciclo sem precisar de nenhum código de outro ciclo e sem acesso ao GCP.

**Why this priority**: É a razão de existir do ciclo. Sem contratos em código e fakes, os ciclos da Onda 1 não podem rodar em paralelo.

**Independent Test**: Numa máquina sem credenciais GCP e sem rede (dependências já instaladas), rodar a suíte dos dois projetos com o modo fake ligado e ver tudo verde; importar os modelos e as interfaces de domínio e obter dados das fakes para o usuário-âncora e o de controle.

**Acceptance Scenarios**:

1. **Given** `main` com o ciclo 000 mergeado, **When** a suíte dos dois projetos roda com o modo fake ligado e sem rede, **Then** todos os testes e o lint passam.
2. **Given** as fixtures do usuário-âncora e do de controle, **When** a fake do repositório financeiro é consultada para o perfil mensal do controle até 202503, **Then** devolve 3 meses do controle e nenhum do âncora.
3. **Given** o DDL de cada tabela e o modelo tipado correspondente, **When** o teste de contrato compara os dois, **Then** nomes e tipos das colunas coincidem em 100% das tabelas.

---

### User Story 2 - Mock do MCP serve as ferramentas com os schemas exatos (Priority: P1)

Uma pessoa que constrói o agente, o canal da demo ou o acompanhamento sobe o MCP mock localmente e o consome como se fosse o real: as 8 ferramentas (7 P0 mais `resumo_mes`) aparecem com os parâmetros de contratos §5, respondem com o envelope de sucesso ou de erro e usam as fixtures como fonte.

**Why this priority**: Desbloqueia 004, 006 e 007, que dependem de um servidor de ferramentas antes de o 003 existir.

**Independent Test**: Subir o mock, listar as ferramentas com um cliente MCP e chamar cada uma com o usuário-âncora, com um UUID desconhecido e com um UUID malformado.

**Acceptance Scenarios**:

1. **Given** o mock no ar, **When** um cliente MCP lista as ferramentas, **Then** aparecem as 8 ferramentas com os parâmetros de contratos §5.
2. **Given** o usuário-âncora, **When** `perfil_financeiro` é chamada com `ate_anomes = 202506`, **Then** a resposta é o golden `__ate_202506` acompanhado de um aviso de mock; com `202512`, é o golden `__ate_202512`.
3. **Given** um UUID válido que não consta em `usuarios.json`, **When** qualquer ferramenta é chamada, **Then** retorna o erro `USUARIO_INEXISTENTE` como resultado (não como exceção).
4. **Given** um UUID malformado, **When** qualquer ferramenta é chamada, **Then** retorna `ENTRADA_INVALIDA`.
5. **Given** `simular_objetivo` com `prazo_meses` e `aporte_mensal` juntos, ou `ate_anomes = 202601`, **When** chamada, **Then** retorna `ENTRADA_INVALIDA`.

---

### User Story 3 - Agente hello e pontos de extensão para 004, 005 e 006 (Priority: P1)

Uma pessoa que constrói a jornada (004), a governança (005) ou o acompanhamento (006) parte de um agente mínimo que já conecta ao MCP, instala os quatro callbacks agregados e carrega extensões opcionais. Ela registra ferramentas, instruções e callbacks nos pontos de extensão, sem editar o `agent.py` do 004.

**Why this priority**: Evita conflito de merge entre 004, 005 e 006 sobre o mesmo arquivo do agente.

**Independent Test**: Rodar os testes do encadeador de callbacks, do registro de extensões e da persistência em memória, e o teste sem LLM em que o agente conecta ao mock e lista as ferramentas.

**Acceptance Scenarios**:

1. **Given** duas funções registradas na mesma fase com ordens 10 e 20, **When** a de ordem 10 retorna um valor não nulo, **Then** a de ordem 20 não executa; as quatro fases (`before_model`, `after_model`, `before_tool`, `after_tool`) funcionam assim.
2. **Given** que os pacotes de governança e de acompanhamento ainda não existem, **When** as extensões são carregadas, **Then** o carregamento termina sem erro.
3. **Given** o registro em memória, **When** usado no lugar do registro de aplicação, **Then** cumpre o mesmo contrato (planos, consentimentos, eventos, acompanhamentos, consulta de plano).
4. **Given** o mock local no ar, **When** o agente conecta via a conexão MCP, **Then** lista as ferramentas sem chamar nenhum LLM.
5. **Given** o agente hello local com acesso a um modelo, **When** a pessoa pergunta "qual é o meu perfil financeiro?", **Then** o agente chama `perfil_financeiro` e o resultado do smoke fica registrado em `smoke.md`. *(exige LLM/GCP)*

---

### User Story 4 - Convenções, governança e comandos do repositório (Priority: P2)

Uma pessoa nova no time clona o repositório e sabe, pelo `CLAUDE.md` e pelo `Makefile`, como testar, rodar o mock, rodar o agente, regenerar fixtures e onde ficam os contratos. A constituição fixa os princípios de governança que valem para todos os ciclos.

**Why this priority**: Reduz atrito e evita violações dos princípios (números, escopo, segredos), mas é menos crítico que os contratos e o mock.

**Independent Test**: Ler o `CLAUDE.md`, rodar cada target do `Makefile` e conferir a constituição contra os princípios listados no ciclo.

**Acceptance Scenarios**:

1. **Given** o repositório recém-clonado, **When** `make test` e `make lint` rodam, **Then** executam nos dois projetos e terminam verdes.
2. **Given** a constituição, **When** conferida, **Then** contém os princípios de números determinísticos, escopo por cliente somente leitura, dados sintéticos, consentimento e segredos, testes obrigatórios, contratos só via PR `contracts:` e regras de paralelismo.

---

### User Story 5 - Plataforma GCP validada e pipeline de deploy (Priority: P2)

Um integrante com credenciais GCP valida que os datasets podem ser criados de forma idempotente, que os IDs de modelo (Gemini Flash e embedding) respondem, e que as imagens dos dois serviços são construídas, enviadas ao Artifact Registry e publicadas em Cloud Run (MCP privado). O resultado alimenta a decisão entre Plano A e Plano B de IAM.

**Why this priority**: Reduz o risco de descobrir só na integração final que um modelo, uma permissão ou o pipeline de deploy não funciona. Depende de credenciais que nem todo ambiente tem.

**Independent Test**: Rodar o script de DDL duas vezes e ver a segunda sem alteração; rodar o smoke de modelos e ver os IDs gravados; rodar build, push e deploy e chamar o MCP privado com um ID token.

**Acceptance Scenarios**:

1. **Given** credenciais GCP do integrante, **When** o script de DDL roda pela segunda vez, **Then** nenhum dataset ou tabela é alterado.
2. **Given** a lista de Gemini Flash 3.8 → 3.7 → 3.5, **When** o smoke roda, **Then** o primeiro que responde é gravado em `contracts/env.example`, junto com o ID de embedding, e o relatório de latência e dimensão vai para `modelos.md`.
3. **Given** as imagens publicadas, **When** o MCP privado é chamado com um ID token de um integrante, **Then** responde; sem token, é recusado.

---

### User Story 6 - Pedidos ao owner e decisão Plano A/B (Priority: P3)

Quem faz a ponte com o owner do projeto GCP recebe os quatro pedidos de desbloqueio já redigidos e prontos para envio, com o status e a decisão Plano A ou B registrados no repositório.

**Why this priority**: É um insumo de decisão, não bloqueia o desenvolvimento offline dos ciclos.

**Independent Test**: Abrir `pedidos-owner.md` e conferir os 4 itens do contexto mestre §16 e o registro da decisão.

**Acceptance Scenarios**:

1. **Given** o contexto mestre §16, **When** `pedidos-owner.md` é lido, **Then** contém os 4 itens (service account de runtime com os papéis listados, template de Model Armor, bucket, confirmação de `allUsers` como invoker) prontos para envio.
2. **Given** a resposta ainda pendente do owner, **When** o ciclo é entregue, **Then** o status "pendente" e o caminho Plano B preparado estão registrados.

---

### Edge Cases

- `id_usuario` fora do formato UUID v4, vazio ou muito longo → `ENTRADA_INVALIDA` (nunca exceção não tratada).
- `ate_anomes` fora de `202501`–`202512`, ou `anomes` de `resumo_mes` maior que `ate_anomes` → `ENTRADA_INVALIDA`.
- `top_n` fora de 1–10, `k` fora de 1–10, `prazo_meses` fora de 1–360, `valor_alvo` ≤ 0, `pergunta` com mais de 500 caracteres → `ENTRADA_INVALIDA`.
- `simular_objetivo` sem nenhum entre `prazo_meses` e `aporte_mensal`, ou com os dois → `ENTRADA_INVALIDA`.
- Chamada ao mock com `ate_anomes` menor que `202512` e diferente de `202506`: recebe o golden `__ate_202506` com aviso de mock (comportamento de contratos §8), sem fingir que é dado real.
- Usuário conhecido que não é o âncora (o de controle) chamando o mock: `DADOS_INSUFICIENTES`; nenhum dado do âncora é devolvido a ele.
- Função de callback que devolve `None`: a cadeia continua; a que devolve valor não nulo interrompe.
- Pacote de extensão ausente (`ImportError`): ignorado; qualquer outro erro dentro do pacote presente não é engolido.
- Segunda execução do DDL ou do build/deploy: não altera o que já existe.
- Ambiente sem `gcloud`, sem ADC ou sem rede: as partes offline funcionam e as que exigem GCP ficam explicitamente pendentes, sem simular sucesso.
- Valor de `gemini-api-key` ou de qualquer token nunca aparece em log, saída de script, `env.example` ou commit.

## Requirements *(mandatory)*

### Functional Requirements

**Governança e convenções**

- **FR-001**: O repositório MUST ter o Spec Kit inicializado com a integração Claude e uma constituição com os princípios do ciclo: números só de ferramentas determinísticas; agente sem ver SQL/infraestrutura; acesso somente leitura com escopo de `id_usuario`; diagnóstico, simulação e recomendação rotulados; só dados sintéticos; consentimento explícito e auditado; segredos fora do repositório; pt-BR e Responsible AI; testes obrigatórios para simulação, validação e contratos MCP; contratos só via PR `contracts:`; propriedade de diretórios; fakes antes de dependências não mergeadas; testes só gravam em `bussola_app_dev`; Cloud Run `--no-traffic` fora do 007.
- **FR-002**: O repositório MUST ter um `CLAUDE.md` na raiz com: comandos `make`, modo `BUSSOLA_FAKES`, onde ficam os contratos, tabela de propriedade (link para contratos §1), proibição de SQL concatenado e de logar prompts ou segredos, e o fluxo de PR.
- **FR-003**: O `.gitignore` existente MUST ser preservado, acrescentando apenas o que faltar.
- **FR-004**: O `Makefile` MUST ter os targets `test`, `lint`, `mcp`, `agent`, `fixtures` e `test-bq`, com o comportamento de contratos §2 (testes e lint nos dois projetos; MCP local na porta 8080; agente local com ADK Web; regeneração das fixtures; testes de BigQuery real fora do padrão).

**Projetos**

- **FR-005**: MUST existir dois projetos independentes, `mcp_server/` e `agent/`, cada um com as dependências do ciclo §3.2 e com a definição de imagem de contêiner do respectivo serviço (porta `$PORT`, padrão 8080, arquitetura `linux/amd64`; o agente serve o ADK Web UI).

**Contratos em código**

- **FR-006**: MUST existir o DDL de `bussola_dados`, `bussola_rag` e `bussola_app` em `contracts/bigquery/`, com as tabelas e colunas de contratos §3; `bussola_app_dev` MUST reutilizar o DDL de `bussola_app`.
- **FR-007**: MUST existir `contracts/env.example` com as variáveis de contratos §7 e **sem valores secretos**.
- **FR-008**: MUST existir o conjunto de modelos tipados de I/O: linhas de contratos §3; entrada e `dados` de cada ferramenta de §5; envelopes `Resposta`, `Fonte`, `Periodo` e `Erro`; e o enum de códigos de erro (`USUARIO_INEXISTENTE`, `ENTRADA_INVALIDA`, `PRAZO_IMPLAUSIVEL`, `DADOS_INSUFICIENTES`, `INDISPONIVEL`).
- **FR-009**: MUST existir as interfaces de domínio `RepositorioFinanceiro` e `BuscadorContexto` (contratos §4) e implementações fake de ambas sobre `contracts/fixtures/`.
- **FR-010**: Os dois serviços MUST ter logger JSON conforme contratos §9 (uma linha por evento, compatível com Cloud Logging, com os campos listados) que **nunca** registra prompt completo, texto de lançamentos, chaves ou tokens.
- **FR-011**: O agente MUST ter as chaves de `session.state` e o enum `estado_jornada` de contratos §6, com helpers de leitura e escrita.
- **FR-012**: O agente MUST ter o encadeador `registrar(fase, funcao, ordem)` para as fases `before_model`, `after_model`, `before_tool` e `after_tool`, que executa em ordem crescente e interrompe no primeiro retorno não nulo, e os 4 callbacks agregados.
- **FR-013**: O agente MUST ter o registro de extensões (`registrar_ferramenta`, `registrar_instrucao`, `ferramentas`, `instrucoes`, `carregar_extensoes`), com as faixas de ordem de instrução reservadas de contratos §6; `carregar_extensoes()` MUST tolerar pacotes ausentes.
- **FR-014**: O agente MUST ter o contrato de persistência `RegistroApp`, os modelos `Plano`, `Consentimento`, `EventoAuditoria` e `Acompanhamento`, e o fake `RegistroEmMemoria`.
- **FR-015**: O agente MUST ter a conexão MCP (streamable HTTP, com ID token OIDC opcional via `MCP_USE_OIDC`) e a chamada direta `chamar_ferramenta`, que força `id_usuario` e `ate_anomes` a partir do `state`.

**Fixtures e mock**

- **FR-016**: MUST existir o gerador de fixtures que, a partir da base de origem em modo somente leitura, produz `contracts/fixtures/` (usuários âncora e controle, 12 meses; `usuarios.json`, `bussola_dados/<tabela>.json`, goldens `ferramentas/<ferramenta>__ate_202506.json` e `__ate_202512.json`, `resumo_mes__<AAAAMM>.json` de 202501 a 202512), com goldens **provisórios** calculados por implementação de referência simples no próprio gerador, e as entradas fixas usadas em cada golden documentadas junto dele. Sem acesso à base de origem, o gerador MUST oferecer um modo de teste sobre um extrato sintético mínimo e determinístico; as fixtures commitadas por este ciclo MUST ser rotuladas como **provisórias sintéticas** (a origem consta em `usuarios.json`) até serem regeneradas da base real por PR `contracts:`. A verificação dos valores de referência do âncora (1%) MUST rodar apenas contra fixtures geradas da base real e fica como pendência declarada enquanto não houver credenciais.
- **FR-017**: MUST existir `contracts/fixtures/rag/trechos_exemplo.json` com trechos determinísticos no formato de `buscar_contexto_financeiro`, cobrindo o âncora e um trecho de `coorte`.
- **FR-018**: O MCP mock MUST registrar as 7 ferramentas P0 e `resumo_mes` com as assinaturas de contratos §5, validar a entrada e responder a partir das fixtures: `ate_anomes < 202512` recebe o golden `__ate_202506` com aviso de mock; `ate_anomes = 202512` recebe o golden `__ate_202512`. Os argumentos livres (`top_n`, `valor_alvo`, `prazo_meses`, `aporte_mensal`, `usar_saldo_atual`) são validados, mas não alteram o golden devolvido; `buscar_contexto_financeiro` responde a partir de `rag/trechos_exemplo.json`; `resumo_mes` responde com o `resumo_mes__<AAAAMM>.json` do `anomes` pedido.
- **FR-019**: O MCP mock MUST devolver `USUARIO_INEXISTENTE` para UUID válido ausente de `usuarios.json` e `ENTRADA_INVALIDA` para UUID malformado, `ate_anomes` fora do intervalo ou combinação inválida de argumentos, sempre como envelope de erro no resultado da ferramenta. Para um usuário conhecido que não é o âncora (o de controle), MUST devolver `DADOS_INSUFICIENTES`, sem devolver nenhum dado do âncora.
- **FR-020**: O agente hello MUST ter um `root_agent` com a conexão MCP, instrução mínima em pt-BR, os 4 callbacks agregados instalados com cadeias vazias e chamada a `carregar_extensoes()`; MUST NOT conter lógica de negócio. O smoke manual do agente hello local — responder "qual é o meu perfil financeiro?" chamando `perfil_financeiro` — MUST ser registrado em `specs/000-fundacao-contratos/smoke.md`.

**Plataforma GCP**

- **FR-021**: MUST existir um script de DDL que cria de forma idempotente os datasets `bussola_dados`, `bussola_rag`, `bussola_app` e `bussola_app_dev`, com as suas tabelas, em `us-central1`.
- **FR-022**: MUST existir um script de smoke de modelos que valida o ID do Gemini Flash (ordem 3.8 → 3.7 → 3.5, o primeiro que responder) e do modelo de embedding via Vertex com credenciais do integrante, grava os IDs em `contracts/env.example` e o relatório (modelos testados, latência, dimensão do embedding) em `specs/000-fundacao-contratos/modelos.md`. Se nenhum Flash responder via Vertex, registra o fato e testa via Gemini API, lendo a chave do Secret Manager na hora, sem imprimi-la.
- **FR-023**: MUST existir os scripts de build/push (tag = SHA curto, Artifact Registry `agentes`) e de deploy (com `--tag cNNN --no-traffic` opcional) que publicam `bussola-mcp` (mock, **privado**) e `bussola-agent` (hello) e registram o que funcionou com a service account default (insumo da decisão Plano A/B).
- **FR-024**: MUST existir o script do Plano B de IAM em nível de dataset (`dataViewer` em `bussola_dados` e `bussola_rag`; `dataEditor` em `bussola_app` e `bussola_app_dev`) para a service account default, executável apenas por um integrante **com confirmação humana**; o agente do Spec Master MUST NOT executá-lo.
- **FR-025**: MUST existir `specs/000-fundacao-contratos/pedidos-owner.md` com os 4 itens do contexto mestre §16 prontos para envio, e o status e a decisão Plano A/B registrados; o agente MUST NOT enviar mensagens.

**Processo e qualidade**

- **FR-026**: MUST existir uma suíte de testes offline (sem rede nem GCP, modo fake ligado) cobrindo: coincidência DDL ↔ modelos; schema das ferramentas do mock ↔ contratos §5; encadeador de callbacks; extensões; `RegistroEmMemoria`; fakes; e a conexão do agente ao mock sem LLM.
- **FR-027**: Divergências entre contratos e implementação MUST ser registradas em `specs/000-fundacao-contratos/questoes.md`, e o contrato MUST ser corrigido no mesmo PR.
- **FR-028**: A rastreabilidade MUST ser exportada para `specs/000-fundacao-contratos/traceability.md`.
- **FR-029**: O canal da demo é a ADK Web UI (Q4 do contexto mestre, decidido em 2026-09-26): o mapa de contratos §1 MUST permanecer sem `web/` e sem ponto de entrada de front em `agent/` neste PR. Uma eventual adoção de front próprio MUST entrar depois por PR `contracts:` aditivo.
- **FR-030**: Após o merge em `main`, a tag `contratos-v1` MUST ser publicada por um integrante; o merge exige revisão de pelo menos 2 pessoas.

### Key Entities *(include if feature involves data)*

- **Contrato v1**: conjunto versionado (`contratos-v1`) de esquemas, modelos, interfaces e convenções que os demais ciclos consomem e só alteram por PR `contracts:`.
- **Usuário sintético (âncora / controle)**: identificador UUID v4; o âncora é o caso de demonstração e o controle serve aos testes negativos de escopo.
- **Linha de dados**: registro de uma das tabelas de contratos §3 (perfil mensal, gastos, entradas, recorrentes, parcelas, categorias, referência de coorte, documentos RAG, planos, consentimentos, auditoria, acompanhamento).
- **Ferramenta MCP**: operação semântica de contratos §5, com parâmetros comuns (`id_usuario`, `ate_anomes`) e entrada adicional própria.
- **Envelope**: resposta padrão de sucesso (`dados`, `fonte`, `avisos`) ou de erro (`codigo`, `mensagem`).
- **Fixture / golden**: dado de exemplo determinístico e o envelope esperado de cada ferramenta, provisórios até o 001.
- **Estado de sessão**: conjunto de chaves de contratos §6 que a jornada, a governança e o acompanhamento leem e escrevem.
- **Extensão**: ferramenta, instrução ou callback registrado por outro ciclo sem editar o agente base.
- **Pedido ao owner**: solicitação de desbloqueio de IAM/recursos (contexto mestre §16), com status e decisão Plano A/B.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em uma máquina sem credenciais GCP e sem rede (dependências já instaladas), 100% dos testes e o lint dos dois projetos passam com o modo fake ligado.
- **SC-002**: 100% dos artefatos marcados como do ciclo 000 no mapa de contratos §1 existem no repositório.
- **SC-003**: 100% das colunas do DDL têm campo correspondente (mesmo nome e tipo) nos modelos, e o schema das 8 ferramentas do mock coincide com contratos §5, verificados por teste automatizado.
- **SC-004**: O mock lista exatamente 8 ferramentas e 100% dos casos de erro definidos (UUID desconhecido, UUID malformado, `ate_anomes` inválido, `simular_objetivo` com combinação inválida) devolvem o código de erro esperado como resultado.
- **SC-005**: Os ciclos da Onda 1 (001, 003, 004, 007) conseguem iniciar a partir de `main` sem depender de código de nenhum outro ciclo.
- **SC-006**: Os valores de referência do usuário-âncora nas fixtures (renda, gasto, sobra, aluguel, comer fora, assinaturas, juros, saldo mínimo e máximo) ficam dentro de 1% de contratos §8. *(pendência declarada: só verificável contra fixtures geradas da base real, ver FR-016)*
- **SC-007**: A segunda execução do script de DDL não altera nenhum dataset nem tabela; as duas imagens estão no Artifact Registry e os dois serviços em Cloud Run, com o MCP recusando chamadas sem token. *(depende de credenciais GCP)*
- **SC-008**: Os 4 pedidos ao owner estão redigidos e a decisão Plano A/B está registrada antes do merge; nenhum segredo aparece em nenhum arquivo versionado.

## Assumptions

- Os "usuários" desta feature são o time de desenvolvimento e operação (Pessoas A e B); não há cliente final neste ciclo.
- O ciclo é esqueleto: **nenhuma** lógica de negócio real (métricas, simulação, prompts, gate de consentimento); isso pertence aos ciclos 001–007. As fixtures e goldens são provisórios até o 001.
- "Sem acesso à rede" nos testes significa que a suíte roda sem chamadas externas em tempo de execução; as dependências já foram instaladas antes.
- Para `RegrasCenario` vale a proposta de contratos §4 (0,40/0,60/0,80; rendimento 0; saldo inicial 0) até decisão do time (Q2 do contexto mestre); o 000 não implementa a simulação.
- O resultado dos pedidos ao owner (Q7) é desconhecido; o 000 deixa os Planos A e B preparados e registra a decisão como pendente.
- Os critérios que exigem GCP ao vivo (fixtures reais e checagem de 1%, DDL, smoke de modelos, deploy, smoke do agente com LLM — AC4, AC7, AC11–AC13) dependem de um integrante com `gcloud` e credenciais ADC. Por decisão de 2026-09-26, este run entrega scripts e testes offline e deixa esses critérios como pendência declarada no relatório final, conforme o gate do ciclo (§6), sem dá-los como cumpridos.
- Um front próprio para o canal da demo, se vier a ser escolhido, é tratado por PR `contracts:` aditivo posterior; não faz parte deste ciclo.
- Data-limite e duração da demo não estão definidas (Q1 do contexto mestre); isso não altera o escopo deste ciclo.
- Este ciclo é o dono do contrato até o merge; qualquer divergência achada em contratos é corrigida no mesmo PR.
