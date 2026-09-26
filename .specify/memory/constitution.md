# Constituição da Bússola

## Princípios Fundamentais

### I. Números só de ferramentas determinísticas

O LLM MUST NOT calcular nem inventar números. Todo valor financeiro exibido ao cliente MUST vir
de ferramenta determinística (SQL ou função Python testada); o modelo apenas redige a resposta.
Valores monetários MUST sair das ferramentas como `float` em BRL arredondado a 2 casas;
a formatação (R$, vírgula) é responsabilidade do agente, nunca das ferramentas.

Fonte: contexto mestre §7 e §11; contratos §0.

### II. Escopo por cliente e acesso somente leitura

O agente MUST NOT ver SQL nem infraestrutura. Nenhuma ferramenta MUST aceitar ou devolver SQL,
nomes de projeto ou credenciais. O acesso a dados MUST ser somente leitura e sempre com escopo
de `id_usuario` (UUID v4 validado por regex antes de qualquer uso). O SQL MUST ser sempre
parametrizado (`@id_usuario`, `@ate_anomes`) e MUST NOT ser montado por concatenação de texto
vindo do usuário ou do modelo. `hackathon_dados` é somente leitura; a escrita ocorre apenas em
`bussola_app` (e em `bussola_app_dev` nos testes).

Fonte: contexto mestre §7 e §11; contratos §2 e §5.

### III. Respostas rotuladas e explicáveis

Diagnóstico, simulação e recomendação MUST ser rotulados de forma distinta nas respostas. Toda
resposta que contém número MUST citar a fonte (ferramenta, tabela e período), conforme o
envelope `fonte` de contratos §5. Recomendações MUST citar a fonte e o raciocínio.

Fonte: contexto mestre §7 e §11; contratos §5.

### IV. Dados sintéticos, consentimento e segredos

O projeto MUST usar apenas dados sintéticos. Ação sensível MUST exigir consentimento explícito
do cliente e MUST ser auditada. Segredos MUST ficar fora do repositório: o valor de
`gemini-api-key` ou de qualquer token MUST NOT ser versionado nem impresso. Os textos ao cliente
MUST ser em português do Brasil, com tom de educação financeira e Responsible AI.

Fonte: contexto mestre §11; ciclo 000 §1.7.

### V. Testes obrigatórios (NON-NEGOTIABLE)

Testes MUST existir para funções de simulação, validação de entrada e contratos MCP. `make test`
e `make lint` MUST estar verdes antes de qualquer PR. Os testes MUST rodar offline com
`BUSSOLA_FAKES=TRUE`, sem acesso à rede ou ao GCP. Testes que exigem BigQuery real MUST ser
marcados com `@pytest.mark.bq` e ficar fora do `make test` padrão (`make test-bq`). Testes MUST
gravar somente em `bussola_app_dev`.

Fonte: contexto mestre §12; contratos §2; README de ciclos §5 (regra 9).

### VI. Contratos versionados e aditivos

Os contratos v1 (tag `contratos-v1`) MUST mudar apenas por PR com título `contracts: <mudança>`,
que atualiza `docs/ciclos/contratos.md` e o código de contrato no mesmo commit e recebe revisão
de pelo menos um ciclo consumidor afetado. Mudanças MUST ser aditivas (campo novo opcional,
ferramenta nova); remover ou renomear campo MUST exigir acordo de todos os ciclos ativos. Erros
previstos das ferramentas MUST ser devolvidos como envelope `{"erro": {"codigo", "mensagem"}}`
no resultado, e MUST NOT ser lançados como exceção.

Fonte: contratos §0 e §5; README de ciclos §5 (regra 6).

### VII. Paralelismo seguro

Cada ciclo MUST escrever somente nos seus diretórios, conforme o mapa de contratos §1. Um ciclo
MUST NOT depender de código não mergeado: usa `BUSSOLA_FAKES=TRUE` e as fixtures até a
dependência chegar em `main`. Somente o ciclo 001 escreve em `bussola_dados` e somente o 002
em `bussola_rag`. Publicações em Cloud Run MUST usar `--tag cNNN --no-traffic`; somente o
ciclo 007 move tráfego. Vale 1 ciclo = 1 worktree = 1 branch = 1 sessão Claude Code =
1 execução do Spec Master = 1 feature.

Fonte: README de ciclos §5; ciclo 000 §3.1.

## Restrições Técnicas e de Plataforma

- **Linguagem e projetos:** Python 3.12 com `uv`, em dois projetos independentes (`mcp_server/`
  e `agent/`), um por serviço Cloud Run. Testes com `pytest` e lint/format com `ruff`.
- **Frameworks:** FastMCP com transporte streamable HTTP no MCP; Google ADK no agente.
- **Build e deploy:** build local com `docker buildx --platform linux/amd64`, push para o
  Artifact Registry `agentes` e `gcloud run deploy --image`. `gcloud run deploy --source`,
  `adk deploy` e Agent Runtime MUST NOT ser o caminho padrão, porque exigem bucket de staging
  que o time não pode criar.
- **Serviços bloqueados pela org policy** (Firestore, Cloud SQL, Redis, Scheduler, Tasks,
  Workflows, Eventarc, Compute Engine, GKE, entre outros) MUST NOT ser usados.
- **Logs:** JSON em stdout, uma linha por evento, compatível com Cloud Logging, com os campos
  de contratos §9. Os logs MUST NOT conter prompt completo, texto de lançamentos, chaves ou
  tokens.
- **SQL:** MUST NOT ser concatenado (ver Princípio II).

Fonte: contexto mestre §6 e §13; contratos §2 e §9; `tech-stack.md` do ciclo 000.

## Fluxo de Desenvolvimento e Governança

- Cada ciclo MUST abrir um PR para `main` na ordem de merge do README de ciclos §7, com
  `make test` e `make lint` verdes e rebase em `main` antes do PR.
- O PR do ciclo 000 MUST ser revisado por pelo menos 2 pessoas do time, porque congela os
  contratos; depois do merge, MUST ser criada a tag `contratos-v1`.
- A constituição é congelada no merge do ciclo 000. Os demais ciclos MUST NOT alterá-la: uma
  proposta de mudança MUST ser registrada em `specs/NNN-*/proposta-constituicao.md` e decidida
  pelo time.
- `.spec-master/` é estado local (gitignored). A rastreabilidade de cada ciclo MUST ser
  exportada para `specs/NNN-*/traceability.md` e versionada.

Fonte: ciclo 000 §1.4 e §6; README de ciclos §5 e §7.

## Governança

Esta constituição prevalece sobre as demais práticas do projeto. Emendas MUST seguir a regra de
congelamento acima, ser registradas por escrito e incrementar a versão por SemVer: MAJOR para
remoção ou redefinição incompatível de princípio; MINOR para princípio novo ou orientação
materialmente expandida; PATCH para esclarecimentos e ajustes de redação. Todo PR e toda revisão
MUST verificar a conformidade com estes princípios; desvios MUST ser justificados no PR. O
guia de desenvolvimento em tempo de execução é o `CLAUDE.md` da raiz, criado pelo ciclo 000.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): definir na data do merge do PR do ciclo 000 (tag `contratos-v1`) | **Last Amended**: 2026-09-26
