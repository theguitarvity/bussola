# Modelos validados — ciclo 000

**STATUS: PENDENTE — não executado (sem `gcloud`/ADC no ambiente de desenvolvimento).**

Este arquivo é **sobrescrito** por `deploy/smoke_modelos.py` quando alguém com credenciais o executa:

```bash
gcloud auth application-default login
uv run --project agent python deploy/smoke_modelos.py            # Vertex
uv run --project agent python deploy/smoke_modelos.py --fallback-api   # se nenhum Flash responder no Vertex
```

O script grava `BUSSOLA_MODEL` e `EMBEDDING_MODEL` em `contracts/env.example` (hoje **vazios**) e o relatório
(modelos testados, latência, dimensão do embedding) aqui. Os candidatos padrão são suposições derivadas do
Model Garden (mestre §5), **não confirmadas**: `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.5-flash` e, para
embedding, `gemini-embedding-001`, `text-embedding-005`. Critério AC12 do ciclo 000: **pendente**.
