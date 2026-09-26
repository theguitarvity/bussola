"""Contrato de dados: cada tabela do DDL tem um modelo Pydantic de mesmos nomes e tipos (AC3)."""

import pytest

from bussola_mcp import contratos as c

from ._ddl import campos_do_modelo, ler_sql, tabelas_do_ddl

MODELOS_DADOS = {
    "perfil_mensal": c.PerfilMes,
    "gastos_categoria": c.GastoCategoria,
    "entradas_categoria": c.EntradaCategoria,
    "recorrentes": c.Recorrente,
    "parcelas": c.Parcela,
    "categorias": c.Categoria,
    "referencia_coorte": c.RefCoorte,
}
MODELOS_RAG = {"documentos": c.Documento}


@pytest.mark.parametrize(
    ("sql", "modelos"), [("bussola_dados", MODELOS_DADOS), ("bussola_rag", MODELOS_RAG)]
)
def test_todas_as_tabelas_tem_modelo_e_vice_versa(sql, modelos):
    assert set(tabelas_do_ddl(sql)) == set(modelos)


@pytest.mark.parametrize(
    ("sql", "tabela", "modelo"),
    [("bussola_dados", t, m) for t, m in MODELOS_DADOS.items()]
    + [("bussola_rag", t, m) for t, m in MODELOS_RAG.items()],
)
def test_colunas_do_ddl_batem_com_o_modelo(sql, tabela, modelo):
    assert tabelas_do_ddl(sql)[tabela] == campos_do_modelo(modelo)


@pytest.mark.parametrize("sql", ["bussola_dados", "bussola_rag", "bussola_app"])
def test_ddl_e_idempotente_e_na_regiao_do_projeto(sql):
    texto = ler_sql(sql)
    schema = 'CREATE SCHEMA IF NOT EXISTS `{project}.{dataset}` OPTIONS(location="us-central1")'
    assert schema in texto
    assert texto.count("CREATE TABLE") == texto.count("CREATE TABLE IF NOT EXISTS")
