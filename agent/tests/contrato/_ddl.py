"""Parser mínimo de DDL BigQuery para o teste de contrato DDL <-> modelos Pydantic.

Lê `contracts/bigquery/<nome>.sql` (com os placeholders `{project}` e `{dataset}`) e devolve, por
tabela, `{coluna: (tipo_python, anulavel)}`. Mapa de tipos: research.md R11.
"""

import re
import types
from datetime import datetime
from pathlib import Path
from typing import Union, get_args, get_origin

RAIZ = Path(__file__).resolve().parents[3]

TIPOS = {
    "STRING": str,
    "INT64": int,
    "FLOAT64": float,
    "BOOL": bool,
    "TIMESTAMP": datetime,
    "JSON": dict,
    "ARRAY<FLOAT64>": list[float],
}

_TABELA = re.compile(
    r"CREATE TABLE IF NOT EXISTS\s+`\{project\}\.\{dataset\}\.(\w+)`\s*\((.*?)\)\s*;", re.S
)


def ler_sql(nome: str) -> str:
    return (RAIZ / "contracts" / "bigquery" / f"{nome}.sql").read_text(encoding="utf-8")


def tabelas_do_ddl(nome: str) -> dict[str, dict[str, tuple[type, bool]]]:
    """{tabela: {coluna: (tipo_python, anulavel)}}; ARRAY nunca é anulável (é REPEATED)."""
    sem_comentarios = re.sub(r"--[^\n]*", "", ler_sql(nome))
    resultado = {}
    for tabela, corpo in _TABELA.findall(sem_comentarios):
        colunas = {}
        for linha in filter(None, (c.strip() for c in corpo.split(","))):
            partes = linha.split(None, 1)
            coluna, resto = partes[0], partes[1]
            not_null = resto.upper().endswith("NOT NULL")
            tipo_sql = re.sub(r"\s*NOT NULL$", "", resto, flags=re.I).strip().upper()
            tipo = TIPOS[tipo_sql]
            colunas[coluna] = (tipo, not not_null and not tipo_sql.startswith("ARRAY"))
        resultado[tabela] = colunas
    return resultado


def campos_do_modelo(modelo) -> dict[str, tuple[type, bool]]:
    """{campo: (tipo_python, anulavel)} de um modelo Pydantic."""
    return {nome: _normaliza(info.annotation) for nome, info in modelo.model_fields.items()}


def _normaliza(anotacao) -> tuple[type, bool]:
    origem = get_origin(anotacao)
    if origem in (Union, types.UnionType):
        restantes = [a for a in get_args(anotacao) if a is not type(None)]
        return _normaliza(restantes[0])[0], True
    if origem is dict:
        return dict, False
    if origem is list:
        return (list[float] if get_args(anotacao) == (float,) else list), False
    return anotacao, False
