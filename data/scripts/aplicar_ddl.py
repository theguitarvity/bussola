"""Aplica o DDL de `contracts/bigquery/` no BigQuery, de forma idempotente (contratos §3; FR-021).

Cria `bussola_dados`, `bussola_rag`, `bussola_app` e `bussola_app_dev` (mesmo DDL do `bussola_app`),
em `us-central1`, com todas as tabelas. Só há `CREATE ... IF NOT EXISTS`, então uma segunda execução
não altera nada. Uso (a partir da raiz, com credenciais ADC do integrante):

    uv run --project mcp_server python data/scripts/aplicar_ddl.py            # aplica
    uv run --project mcp_server python data/scripts/aplicar_ddl.py --dry-run  # só imprime o SQL

`--dry-run` nunca abre conexão. O projeto vem de `--projeto` ou `GOOGLE_CLOUD_PROJECT` e é validado
antes de entrar no texto do SQL.
"""

import argparse
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROJETO_PADRAO = "batalha-time-07-lkbv"
REGIAO = "us-central1"
# (arquivo SQL, dataset): o DDL de bussola_app também cria o bussola_app_dev (dataset de testes).
PLANO = (
    ("bussola_dados", "bussola_dados"),
    ("bussola_rag", "bussola_rag"),
    ("bussola_app", "bussola_app"),
    ("bussola_app", "bussola_app_dev"),
)
_ID_PROJETO = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")


def instrucoes(projeto: str) -> list[str]:
    """Instruções DDL (sem `;`) já com `{project}` e `{dataset}` substituídos."""
    if not _ID_PROJETO.match(projeto):
        raise SystemExit(f"projeto GCP inválido: {projeto!r}")
    saida = []
    for arquivo, dataset in PLANO:
        texto = (RAIZ / "contracts" / "bigquery" / f"{arquivo}.sql").read_text(encoding="utf-8")
        texto = re.sub(r"--[^\n]*", "", texto)
        texto = texto.replace("{project}", projeto).replace("{dataset}", dataset)
        saida += [s.strip() for s in texto.split(";") if s.strip()]
    return saida


def _cliente(projeto: str):
    from google.cloud import bigquery

    return bigquery.Client(project=projeto, location=REGIAO)


def aplicar(cliente, projeto: str) -> None:
    """Executa cada instrução no `cliente` (um `bigquery.Client`, injetável em testes)."""
    for sql in instrucoes(projeto):
        cliente.query(sql).result()
        print("ok:", " ".join(sql.split())[:90])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="só imprime o SQL, sem conectar")
    ap.add_argument("--projeto", default=os.environ.get("GOOGLE_CLOUD_PROJECT", PROJETO_PADRAO))
    args = ap.parse_args(argv)
    if args.dry_run:
        for sql in instrucoes(args.projeto):
            print(sql + ";\n")
        return 0
    aplicar(_cliente(args.projeto), args.projeto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
