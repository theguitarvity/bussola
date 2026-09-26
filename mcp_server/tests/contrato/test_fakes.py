"""Fakes sobre as fixtures (FR-009): escopo por usuário, Protocols e filtro do buscador."""

import pytest

from bussola_mcp.dominio.fakes import BuscadorFake, RepositorioFake
from bussola_mcp.dominio.interfaces import BuscadorContexto, RepositorioFinanceiro

ANCORA = "36a21505-d6d4-42d3-b319-d51a133c7269"
CONTROLE = "31e94f2f-1463-49f9-a41a-b3f220ed976a"
DESCONHECIDO = "00000000-0000-4000-8000-000000000000"


@pytest.fixture(scope="module")
def repo():
    return RepositorioFake()


def test_fakes_cumprem_os_protocols():
    assert isinstance(RepositorioFake(), RepositorioFinanceiro)
    assert isinstance(BuscadorFake(), BuscadorContexto)


def test_perfil_mensal_do_controle_ate_202503_tem_3_meses_e_nenhum_do_ancora(repo):
    linhas = repo.perfil_mensal(CONTROLE, 202503)
    assert [linha.anomes for linha in linhas] == [202501, 202502, 202503]
    assert {linha.id_usuario for linha in linhas} == {CONTROLE}


def test_usuario_existe(repo):
    assert repo.usuario_existe(ANCORA) is True
    assert repo.usuario_existe(CONTROLE) is True
    assert repo.usuario_existe(DESCONHECIDO) is False


def test_consultas_respeitam_escopo_e_corte(repo):
    for consulta in (
        repo.gastos_categoria,
        repo.entradas_categoria,
        repo.recorrentes,
        repo.parcelas,
    ):
        linhas = consulta(ANCORA, 202506)
        assert linhas
        assert {linha.id_usuario for linha in linhas} == {ANCORA}
        assert max(linha.anomes for linha in linhas) <= 202506
    assert repo.perfil_mensal(DESCONHECIDO, 202512) == []


def test_gastos_categoria_desde_anomes(repo):
    linhas = repo.gastos_categoria(ANCORA, 202512, desde_anomes=202510)
    assert {linha.anomes for linha in linhas} == {202510, 202511, 202512}


def test_categorias_e_referencia_coorte(repo):
    assert repo.categorias()
    assert any(cat.discricionaria for cat in repo.categorias())
    assert repo.referencia_coorte("ate_3k") == []


def test_buscador_so_devolve_o_proprio_usuario_e_coorte():
    buscador = BuscadorFake()
    trechos = buscador.buscar(ANCORA, "quanto gasto com comer fora?", 10, 202512)
    assert trechos
    for trecho in trechos:
        assert trecho.origem.id_usuario in (ANCORA, None)
        if trecho.origem.id_usuario is None:
            assert trecho.tipo == "coorte"
    assert CONTROLE not in {t.origem.id_usuario for t in trechos}


def test_buscador_respeita_corte_temporal_e_k():
    buscador = BuscadorFake()
    ate_202506 = buscador.buscar(ANCORA, "perfil do ano", 10, 202506)
    assert all(t.anomes is None or t.anomes <= 202506 for t in ate_202506)
    assert all(t.tipo != "perfil_anual" for t in ate_202506)  # perfil_anual usa anomes=202512
    assert len(buscador.buscar(ANCORA, "gasto", 1, 202512)) == 1
