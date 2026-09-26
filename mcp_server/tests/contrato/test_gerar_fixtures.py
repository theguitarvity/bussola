"""Gerador de fixtures (FR-016/017): modo sintético determinístico, válido, busca segura."""

import json
import statistics
from pathlib import Path

import pytest

from bussola_mcp import contratos as c

from ._scripts import carregar

gf = carregar("data/scripts/gerar_fixtures.py")

MESES = list(range(202501, 202513))
MODELOS_TABELA = {
    "perfil_mensal": c.PerfilMes,
    "gastos_categoria": c.GastoCategoria,
    "entradas_categoria": c.EntradaCategoria,
    "recorrentes": c.Recorrente,
    "parcelas": c.Parcela,
    "categorias": c.Categoria,
    "referencia_coorte": c.RefCoorte,
}
GOLDENS = [
    "perfil_financeiro",
    "capacidade_poupanca",
    "oportunidades_corte",
    "dividas_e_parcelas",
    "simular_objetivo",
    "comparar_cenarios",
]


def _ler(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def destino(tmp_path_factory) -> Path:
    pasta = tmp_path_factory.mktemp("fixtures")
    gf.gerar(pasta, gf.extrato_sintetico(), origem="sintetico_teste")
    return pasta


def test_modo_sintetico_e_deterministico(destino, tmp_path):
    gf.gerar(tmp_path, gf.extrato_sintetico(), origem="sintetico_teste")
    arquivos = sorted(p.relative_to(destino) for p in destino.rglob("*.json"))
    assert arquivos == sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*.json"))
    for rel in arquivos:
        assert (destino / rel).read_bytes() == (tmp_path / rel).read_bytes(), rel


def test_usuarios_e_origem(destino):
    usuarios = [c.UsuarioFixture(**u) for u in _ler(destino / "usuarios.json")]
    assert {(u.id_usuario, u.papel) for u in usuarios} == {
        ("36a21505-d6d4-42d3-b319-d51a133c7269", "ancora"),
        ("31e94f2f-1463-49f9-a41a-b3f220ed976a", "controle"),
    }
    assert {u.origem for u in usuarios} == {"sintetico_teste"}


def test_tabelas_dois_usuarios_doze_meses_e_validas(destino):
    for tabela, modelo in MODELOS_TABELA.items():
        linhas = _ler(destino / "bussola_dados" / f"{tabela}.json")
        for linha in linhas:
            modelo.model_validate(linha)
    assert _ler(destino / "bussola_dados" / "referencia_coorte.json") == []
    perfil = _ler(destino / "bussola_dados" / "perfil_mensal.json")
    for usuario in {p["id_usuario"] for p in perfil}:
        assert [p["anomes"] for p in perfil if p["id_usuario"] == usuario] == MESES
    assert len({p["id_usuario"] for p in perfil}) == 2


@pytest.mark.parametrize("corte", [202506, 202512])
@pytest.mark.parametrize("ferramenta", GOLDENS)
def test_golden_valida_no_envelope_e_no_modelo_de_dados(destino, ferramenta, corte):
    envelope = c.Resposta.model_validate(
        _ler(destino / "ferramentas" / f"{ferramenta}__ate_{corte}.json")
    )
    c.FERRAMENTAS[ferramenta][1].model_validate(envelope.dados)
    assert envelope.fonte.ferramenta == ferramenta
    assert envelope.fonte.periodo == c.Periodo(inicio=202501, fim=corte)
    assert all(t.startswith("bussola_dados.") for t in envelope.fonte.tabelas)


def test_resumo_mes_doze_arquivos_validos(destino):
    for mes in MESES:
        envelope = c.Resposta.model_validate(
            _ler(destino / "ferramentas" / f"resumo_mes__{mes}.json")
        )
        dados = c.DadosResumoMes.model_validate(envelope.dados)
        assert dados.anomes == mes


def test_entradas_fixas_dos_goldens_documentadas(destino):
    assert _ler(destino / "ferramentas" / "_entradas.json") == {
        "oportunidades_corte": {"top_n": 5},
        "simular_objetivo": {"valor_alvo": 60000.0, "prazo_meses": 36},
        "comparar_cenarios": {"valor_alvo": 60000.0, "prazo_meses": 36},
        "buscar_contexto_financeiro": {"pergunta": "quanto gasto com comer fora?", "k": 5},
    }


def test_valores_do_golden_conferem_com_as_tabelas(destino):
    ancora = "36a21505-d6d4-42d3-b319-d51a133c7269"
    perfil = [
        p
        for p in _ler(destino / "bussola_dados" / "perfil_mensal.json")
        if p["id_usuario"] == ancora and p["anomes"] <= 202506
    ]
    golden = _ler(destino / "ferramentas" / "perfil_financeiro__ate_202506.json")["dados"]
    assert golden["meses_considerados"] == 6
    assert golden["renda_media"] == round(statistics.mean(p["renda"] for p in perfil), 2)
    assert golden["sobra_mediana"] == round(statistics.median(p["sobra"] for p in perfil), 2)
    assert golden["saldo"]["atual"] == perfil[-1]["saldo_final"]
    capacidade = _ler(destino / "ferramentas" / "capacidade_poupanca__ate_202506.json")["dados"]
    assert capacidade["desvio_padrao"] == round(statistics.pstdev(p["sobra"] for p in perfil), 2)
    assert capacidade["meses_negativos"] == sum(p["sobra"] < 0 for p in perfil)


def test_trechos_validos_com_ancora_controle_e_coorte(destino):
    trechos = [c.Trecho.model_validate(t) for t in _ler(destino / "rag" / "trechos_exemplo.json")]
    assert {t.tipo for t in trechos} >= {"ficha_mensal", "perfil_anual", "coorte"}
    assert {t.origem.id_usuario for t in trechos} >= {
        "36a21505-d6d4-42d3-b319-d51a133c7269",
        "31e94f2f-1463-49f9-a41a-b3f220ed976a",
        None,
    }
    assert all(t.origem.id_usuario is None for t in trechos if t.tipo == "coorte")


class _Job:
    def __init__(self, linhas):
        self._linhas = linhas

    def result(self):
        return self._linhas


class _ClienteFalso:
    def __init__(self, linhas):
        self.linhas = linhas
        self.chamadas = []

    def query(self, sql, job_config=None):
        self.chamadas.append((sql, job_config))
        return _Job(self.linhas)


def test_busca_real_e_parametrizada_e_somente_leitura():
    ids = [gf.ANCORA, gf.CONTROLE]
    cliente = _ClienteFalso(gf.extrato_sintetico())
    linhas = gf.buscar_linhas(cliente, ids)
    assert linhas == gf.extrato_sintetico()
    ((sql, config),) = cliente.chamadas
    assert sql.lstrip().upper().startswith("SELECT")
    assert ";" not in sql
    assert "hackathon_dados.extrato_sintetico" in sql
    assert "@ids" in sql
    assert all(i not in sql for i in ids)  # UUIDs nunca entram no texto do SQL
    (parametro,) = config.query_parameters
    assert parametro.name == "ids"
    assert list(parametro.values) == ids
