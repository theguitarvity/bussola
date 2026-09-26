"""Persistência do agente (FR-014, AC10): RegistroEmMemoria cumpre o contrato RegistroApp."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bussola_agent import persistencia as p

from ._ddl import campos_do_modelo, tabelas_do_ddl

AGORA = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
USUARIO = "36a21505-d6d4-42d3-b319-d51a133c7269"


def _plano(**extra) -> p.Plano:
    dados = {
        "session_id": "s1",
        "id_usuario": USUARIO,
        "objetivo": "primeiro apartamento",
        "valor_alvo": 60000.0,
        "prazo_meses": 36,
        "cenario": "equilibrado",
        "aporte_mensal": 1666.67,
        "ate_anomes": 202506,
        "criado_em": AGORA,
    }
    return p.Plano(**{**dados, **extra})


def _consentimento(**extra) -> p.Consentimento:
    dados = {
        "session_id": "s1",
        "acao": "criar_plano",
        "decisao": "aceito",
        "texto_apresentado": "Posso criar o plano?",
        "ts": AGORA,
    }
    return p.Consentimento(**{**dados, **extra})


def _evento(**extra) -> p.EventoAuditoria:
    dados = {
        "session_id": "s1",
        "estado": "AGIR",
        "tipo_evento": "plano_criado",
        "resumo": {"plano": "x"},
        "ts": AGORA,
    }
    return p.EventoAuditoria(**{**dados, **extra})


def test_registro_em_memoria_cumpre_o_protocol_registro_app():
    assert isinstance(p.RegistroEmMemoria(), p.RegistroApp)


def test_plano_id_vazio_gera_uuid_e_obter_plano_recupera():
    registro = p.RegistroEmMemoria()
    plano_id = registro.registrar_plano(_plano())
    assert str(uuid.UUID(plano_id)) == plano_id
    plano = registro.obter_plano(plano_id)
    assert plano is not None
    assert plano.plano_id == plano_id
    assert plano.objetivo == "primeiro apartamento"


def test_plano_id_informado_e_preservado_e_desconhecido_devolve_none():
    registro = p.RegistroEmMemoria()
    assert registro.registrar_plano(_plano(plano_id="plano-1")) == "plano-1"
    assert registro.obter_plano("plano-1").plano_id == "plano-1"
    assert registro.obter_plano("nao-existe") is None


def test_consentimento_e_evento_devolvem_id_e_ficam_registrados():
    registro = p.RegistroEmMemoria()
    consent_id = registro.registrar_consentimento(_consentimento())
    evento_id = registro.registrar_evento(_evento())
    assert str(uuid.UUID(consent_id)) == consent_id
    assert str(uuid.UUID(evento_id)) == evento_id
    assert [c.consent_id for c in registro.consentimentos] == [consent_id]
    assert [e.evento_id for e in registro.eventos] == [evento_id]
    assert registro.registrar_consentimento(_consentimento(consent_id="c-1")) == "c-1"


def test_registrar_acompanhamento_guarda_e_nao_devolve_nada():
    registro = p.RegistroEmMemoria()
    acompanhamento = p.Acompanhamento(
        plano_id="plano-1",
        anomes=202507,
        planejado=1666.67,
        realizado=1400.0,
        desvio=-266.67,
        ts=AGORA,
    )
    assert registro.registrar_acompanhamento(acompanhamento) is None
    assert registro.acompanhamentos == [acompanhamento]
    assert acompanhamento.categoria_desvio is None
    assert acompanhamento.acao_sugerida is None


def test_decisao_so_aceita_aceito_ou_recusado():
    assert _consentimento(decisao="recusado").decisao == "recusado"
    with pytest.raises(ValidationError):
        _consentimento(decisao="talvez")


def test_tipo_evento_so_aceita_os_tipos_de_contratos_6():
    assert len(p.TIPOS_EVENTO) == 12
    for tipo in p.TIPOS_EVENTO:
        assert _evento(tipo_evento=tipo).tipo_evento == tipo
    with pytest.raises(ValidationError):
        _evento(tipo_evento="evento_inventado")


@pytest.mark.parametrize(
    ("tabela", "modelo"),
    [
        ("planos", p.Plano),
        ("consentimentos", p.Consentimento),
        ("auditoria", p.EventoAuditoria),
        ("acompanhamento", p.Acompanhamento),
    ],
)
def test_colunas_do_ddl_de_bussola_app_batem_com_os_modelos(tabela, modelo):
    assert tabelas_do_ddl("bussola_app")[tabela] == campos_do_modelo(modelo)


def test_todas_as_tabelas_de_bussola_app_tem_modelo():
    assert set(tabelas_do_ddl("bussola_app")) == {
        "planos",
        "consentimentos",
        "auditoria",
        "acompanhamento",
    }
