# Marcos — ciclo 000 (Fundação e contratos)

Checado em 2026-09-26 (trilha A §1.4 e §3). Branch `000-fundacao-contratos`.

## Marcos de que este ciclo depende

Nenhum. O 000 é a Onda 0 e não tem dependências ([ciclo 000 §6](../../docs/ciclos/000-fundacao-contratos.md)).
Os marcos S1–S6 da trilha A **não se aplicam** a este ciclo.

| Marco | Situação para o 000 | Modo de trabalho |
|---|---|---|
| S0 | É **entregue por** este ciclo (000 em `main` + tag `contratos-v1`). Ainda não publicado | n/a |
| S1–S6 | Não consumidos pelo 000 | n/a |

Nenhuma tarefa fica `[aguarda Sx]` por dependência de marco.

## Dependências externas que limitam a execução local (não são marcos)

| Item | Situação neste ambiente | Consequência |
|---|---|---|
| `gcloud` / `bq` | ausentes | Critérios de §4 que exigem GCP ao vivo ficam como **pendência** (ver abaixo) |
| Credenciais ADC do integrante | não verificadas | idem |
| Resposta do owner (mestre §16, Q7) | UNRESOLVED | Decisão Plano A/B fica registrada como pendente |
| Confirmação humana para `iam_datasets.sh` | exigida pelo ciclo | o agente não executa; só entrega o script |

### Critérios do ciclo 000 §4 que dependem de GCP ao vivo (pendência declarada)

- `aplicar_ddl.py` cria os 4 datasets e as tabelas, com 2ª execução idempotente.
- IDs de Gemini Flash e de embedding validados e gravados em `contracts/env.example`.
- Imagens no AR `agentes` e os 2 serviços publicados em Cloud Run.
- Fixtures com valores de referência do âncora: `gerar_fixtures.py` consulta `hackathon_dados.extrato_sintetico`
  (BigQuery). Sem credenciais, **não há como gerar as fixtures reais**.

O gate do ciclo aceita isso: "critérios da §4, exceto os que dependem do owner, que ficam registrados como pendência".
Os scripts, os testes offline e o desenho ficam entregues; a execução ao vivo é do integrante.
