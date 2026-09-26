# Pedidos ao owner do projeto GCP — ciclo 000

Fonte: contexto mestre §16 e §5. **Este arquivo é o texto pronto; o agente não envia mensagens.** Quem envia é uma
pessoa do time (Pessoa B, no roadmap de 2 pessoas; Pessoa D no de 4).

## Status e decisão

| Item | Situação |
|---|---|
| Envio | **NÃO ENVIADO** (preencher: data, canal, quem enviou) |
| Resposta do owner | **PENDENTE** |
| Decisão Plano A/B (mestre Q7) | **PENDENTE.** Enquanto não houver resposta, seguir o **Plano B** (abaixo), já preparado |
| Data-limite da demo (Q1) | não definida; o time deve informar ao owner para priorizar |

## Mensagem (pronta para enviar)

**Para:** andre.favretto@santodigital.com.br (owner do projeto `batalha-time-07-lkbv`)
**Assunto:** Batalha de Agentes, Time 07: 4 pedidos de IAM/recursos para a Bússola

Olá, André. Somos o Time 07 (Bússola). Só você concede IAM de projeto, e precisamos de 4 coisas para o serviço
rodar em Cloud Run com segurança. Sem elas seguimos por um caminho alternativo (Plano B), que funciona, mas é menos
seguro e mais trabalhoso. Se possível, nos avise o que for ou não for liberado.

1. **Service account de runtime** (nova, por exemplo `bussola-runtime`, ou a default do Compute
   `1061873050224-compute@developer.gserviceaccount.com`) com os papéis:
   - `roles/aiplatform.user`
   - `roles/bigquery.jobUser`
   - `roles/bigquery.dataViewer`
   - `roles/secretmanager.secretAccessor`
   - `roles/modelarmor.user`
   - `roles/logging.logWriter`

   *Por quê:* hoje a SA default só tem Artifact Registry Writer, Logs Writer e Storage Admin; sem estes papéis o
   serviço não chama o Gemini, não lê o BigQuery, não lê o segredo e não usa o Model Armor.

2. **Template do Model Armor** (por exemplo `bussola-guard`), criado por quem tem `roles/modelarmor.admin`
   (o time não tem nenhum papel de Model Armor). *Por quê:* guardrail de entrada/saída do agente; sem ele usamos o
   fallback de callbacks do ADK.

3. **Um bucket** (por exemplo `batalha-time-07-lkbv-bussola`) com Storage Object Admin para o time (o time não
   tem Storage Admin para criar bucket). *Por quê:* habilita `--source`, Cloud Build e staging, se precisarmos.

4. **Confirmar se `allUsers` pode ser invoker no Cloud Run** (política de domínio). *Por quê:* define se o canal da
   demo pode ser público; se não puder, usamos `gcloud run services proxy` / token de identidade na máquina da demo.
   Hoje os dois serviços são publicados **privados**.

Obrigado! Time 07: Carlos Guevara, João Paulo Soares Lopes, Kell Bonassoli, Victor Lucas Lopes.

## Plano B (já preparado; vale se os pedidos não saírem a tempo)

Tudo com os papéis atuais do time (mestre §16):

| Área | Caminho |
|---|---|
| BigQuery | O time (BigQuery Admin) concede `dataViewer` em `bussola_dados`/`bussola_rag` e `dataEditor` em `bussola_app`/`bussola_app_dev` à SA default, **por dataset**: `deploy/iam_datasets.sh` (exige confirmação humana digitada). O runtime lê tabelas pré-agregadas por `list_rows` (`BQ_MODO_LEITURA=memoria`) e grava por streaming insert, sem `jobUser`; a busca vetorial roda em memória (`RAG_BACKEND=numpy`) |
| LLM | Gemini via `generativelanguage` com a `gemini-api-key`, injetada como variável de ambiente no deploy por quem tem accessor (`GOOGLE_GENAI_USE_VERTEXAI=FALSE`, `GOOGLE_API_KEY`). **Menos seguro, aceitável só na PoC e deve ficar registrado como dívida** |
| Guardrails | Callbacks `before_model`/`after_model` do ADK + safety settings |
| Invoker | `run.invoker` do MCP para a SA do agente: o time concede (é Cloud Run Admin) |

O smoke do 000 (`deploy/smoke_modelos.py`, `deploy/deploy.sh`) registra o que funcionou com a SA default e alimenta a
decisão A/B: espera-se que a chamada ao Gemini pelo Cloud Run falhe por falta de IAM.
