"""Chaves de session.state e enum da jornada (FR-011, contratos §6)."""

import pytest

from bussola_agent import estado


def test_as_dez_chaves_de_contratos_6():
    assert estado.CHAVES == frozenset(
        {
            "id_usuario",
            "ate_anomes",
            "estado_jornada",
            "objetivo",
            "cenarios",
            "cenario_escolhido",
            "ultimas_fontes",
            "consentimentos",
            "plano_id",
            "acompanhamento",
        }
    )


def test_constantes_apontam_para_as_chaves():
    assert estado.ID_USUARIO == "id_usuario"
    assert estado.ATE_ANOMES == "ate_anomes"
    assert estado.ESTADO_JORNADA == "estado_jornada"
    assert estado.PLANO_ID == "plano_id"


def test_estado_da_jornada_tem_exatamente_os_seis_estados():
    assert [e.value for e in estado.EstadoJornada] == [
        "OBJETIVO",
        "ENTENDER",
        "ANTECIPAR",
        "ORIENTAR",
        "AGIR",
        "ACOMPANHAR",
    ]
    assert estado.EstadoJornada.AGIR == "AGIR"


def test_escrever_e_ler_num_state_qualquer():
    state = {}
    estado.escrever(state, estado.ATE_ANOMES, 202506)
    estado.escrever(state, estado.ESTADO_JORNADA, estado.EstadoJornada.ENTENDER)
    assert estado.ler(state, estado.ATE_ANOMES) == 202506
    assert estado.ler(state, estado.ESTADO_JORNADA) == "ENTENDER"


def test_ler_chave_ausente_devolve_o_padrao():
    assert estado.ler({}, estado.PLANO_ID) is None
    assert estado.ler({}, estado.PLANO_ID, "sem plano") == "sem plano"


def test_escrever_chave_desconhecida_e_recusado():
    with pytest.raises(ValueError, match="chave"):
        estado.escrever({}, "chave_inventada", 1)


def test_ler_chave_desconhecida_e_recusado():
    with pytest.raises(ValueError, match="chave"):
        estado.ler({}, "chave_inventada")
