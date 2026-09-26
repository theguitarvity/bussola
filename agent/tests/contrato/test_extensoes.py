"""Registro de extensões (FR-013, AC9): tolera pacotes ausentes, não engole erro interno."""

import sys
import textwrap

import pytest

from bussola_agent import extensoes as ext


@pytest.fixture(autouse=True)
def _registro_limpo():
    ext.limpar()
    yield
    ext.limpar()


def _pacote(tmp_path, monkeypatch, nome: str, corpo: str) -> str:
    pasta = tmp_path / nome
    pasta.mkdir()
    (pasta / "__init__.py").write_text(textwrap.dedent(corpo), encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, nome, raising=False)
    return nome


def test_carregar_sem_os_pacotes_de_governanca_e_acompanhamento_nao_levanta():
    ext.carregar_extensoes()  # governanca (005) e acompanhamento (006) ainda não existem
    assert ext.ferramentas() == []
    assert ext.instrucoes() == ""


def test_pacote_presente_registra_suas_ferramentas_e_instrucoes(tmp_path, monkeypatch):
    nome = _pacote(
        tmp_path,
        monkeypatch,
        "pacote_ext_ok",
        """
        from bussola_agent import extensoes

        def criar_plano(cenario):
            return {}

        extensoes.registrar_ferramenta(criar_plano, sensivel=True)
        extensoes.registrar_instrucao(55, "Peça consentimento antes de criar o plano.")
        """,
    )
    monkeypatch.setattr(ext, "PACOTES", (nome, "pacote_ext_ausente"))
    ext.carregar_extensoes()
    assert [f.__name__ for f in ext.ferramentas()] == ["criar_plano"]
    assert ext.sensiveis() == {"criar_plano"}
    assert ext.instrucoes() == "Peça consentimento antes de criar o plano."


def test_importerror_dentro_de_um_pacote_presente_propaga(tmp_path, monkeypatch):
    nome = _pacote(tmp_path, monkeypatch, "pacote_ext_quebrado", "import modulo_que_nao_existe_xyz")
    monkeypatch.setattr(ext, "PACOTES", (nome,))
    with pytest.raises(ImportError, match="modulo_que_nao_existe_xyz"):
        ext.carregar_extensoes()


def test_erro_qualquer_dentro_de_um_pacote_presente_propaga(tmp_path, monkeypatch):
    nome = _pacote(tmp_path, monkeypatch, "pacote_ext_erro", "raise RuntimeError('bug')")
    monkeypatch.setattr(ext, "PACOTES", (nome,))
    with pytest.raises(RuntimeError, match="bug"):
        ext.carregar_extensoes()


def test_pacotes_padrao_sao_governanca_e_acompanhamento():
    assert ext.PACOTES == ("bussola_agent.governanca", "bussola_agent.acompanhamento")


def test_instrucoes_sao_concatenadas_por_ordem_crescente():
    ext.registrar_instrucao(75, "C (acompanhamento)")
    ext.registrar_instrucao(10, "A (jornada)")
    ext.registrar_instrucao(60, "B (governança)")
    assert ext.instrucoes() == "A (jornada)\n\nB (governança)\n\nC (acompanhamento)"


def test_faixas_reservadas_de_instrucao():
    assert ext.FAIXAS_INSTRUCAO == {"004": (0, 49), "005": (50, 69), "006": (70, 89)}


def test_ferramentas_sensiveis_e_livres():
    def ler_algo():
        return 1

    def criar_plano():
        return 2

    ext.registrar_ferramenta(ler_algo)
    ext.registrar_ferramenta(criar_plano, sensivel=True)
    assert [f.__name__ for f in ext.ferramentas()] == ["ler_algo", "criar_plano"]
    assert ext.sensiveis() == {"criar_plano"}


def test_registrar_a_mesma_ferramenta_duas_vezes_nao_duplica():
    def ferramenta():
        return 1

    ext.registrar_ferramenta(ferramenta)
    ext.registrar_ferramenta(ferramenta)
    assert ext.ferramentas() == [ferramenta]
