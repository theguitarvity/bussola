# Quickstart — validar o ciclo 000

Roteiro reproduzível. Aqui **não** há código de implementação: os detalhes estão em `plan.md`, `data-model.md` e `tasks.md`.
Passos marcados **[GCP]** exigem `gcloud`/ADC e ficam como pendência quando indisponíveis (D-001).

## Pré-requisitos

- `uv` (>= 0.9) e Python 3.12 (`uv python install 3.12`); `make`.
- **[GCP]** `gcloud` autenticado (`gcloud auth application-default login`), `docker` com `buildx`, permissões do time (mestre §5).

## A. Offline (obrigatório; sem rede nem GCP nos testes)

```bash
make lint                  # ruff check + ruff format --check, nos dois projetos     → verde
make test                  # pytest nos dois projetos com BUSSOLA_FAKES=TRUE          → verde
make mcp                   # sobe o mock em http://localhost:8080/mcp (Ctrl+C para parar)
```

Com o mock no ar, em outro terminal:

```bash
uv run --project mcp_server python - <<'EOF'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8080/mcp") as c:
        print(sorted(t.name for t in await c.list_tools()))          # 8 ferramentas
        r = await c.call_tool("perfil_financeiro", {"id_usuario": "36a21505-d6d4-42d3-b319-d51a133c7269", "ate_anomes": 202506})
        print(r.data["fonte"], r.data["avisos"])                      # golden __ate_202506 + aviso de mock
        r = await c.call_tool("perfil_financeiro", {"id_usuario": "not-a-uuid", "ate_anomes": 202506})
        print(r.data)                                                 # ENTRADA_INVALIDA
asyncio.run(main())
EOF
```

Esperado: lista com `buscar_contexto_financeiro, capacidade_poupanca, comparar_cenarios, dividas_e_parcelas, oportunidades_corte, perfil_financeiro, resumo_mes, simular_objetivo`; envelope de sucesso com aviso de mock; `{"erro": {"codigo": "ENTRADA_INVALIDA", …}}`.

Regenerar as fixtures **sintéticas de teste** (determinístico, sem BigQuery): `make fixtures ARGS=--sintetico` → o `git status` não muda.

## B. Conferências rápidas

```bash
git grep --untracked -nE "AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----" || echo "sem segredos"
bash -n deploy/build_push.sh deploy/deploy.sh deploy/iam_datasets.sh          # sintaxe ok
python3 data/scripts/aplicar_ddl.py --dry-run                                  # 4 CREATE SCHEMA + tabelas, todos IF NOT EXISTS
```

## C. [GCP] Plataforma (pendência declarada quando sem credenciais)

1. `make fixtures` (base real) → conferir os valores de referência do âncora dentro de 1% (contratos §8); ajustar as regras provisórias de `questoes.md` Q-006 se necessário; PR `contracts:`.
2. `python3 data/scripts/aplicar_ddl.py` **duas vezes** → a 2ª não altera nada.
3. `uv run --project agent python deploy/smoke_modelos.py` → IDs gravados em `contracts/env.example` e `modelos.md`.
4. `deploy/build_push.sh bussola-mcp && deploy/build_push.sh bussola-agent`, depois `deploy/deploy.sh bussola-mcp` e `deploy/deploy.sh bussola-agent` → MCP privado responde com ID token (`gcloud auth print-identity-token`) e recusa sem token; registrar em `deploy.md`.
5. `make agent`, perguntar "qual é o meu perfil financeiro?" → o agente chama `perfil_financeiro`; registrar em `smoke.md`.
6. `deploy/iam_datasets.sh` (Plano B): **só com confirmação humana**.

## D. Fechamento

`specs/000-fundacao-contratos/traceability.md` exportado; PR para `main` revisado por ≥ 2 pessoas; depois do merge: `git tag contratos-v1 && git push origin contratos-v1` (ação humana).
