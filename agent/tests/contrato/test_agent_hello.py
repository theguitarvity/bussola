"""Agente hello (FR-020): mínimo, sem lógica de negócio, com callbacks e extensões instalados."""

import pytest

from bussola_agent import agent, callbacks, extensoes, mcp_conexao


@pytest.fixture(autouse=True)
def _registros_limpos():
    extensoes.limpar()
    yield
    extensoes.limpar()


def test_root_agent_importavel_com_os_4_callbacks_agregados_instalados():
    ra = agent.root_agent
    assert ra.name == "bussola"
    assert ra.before_model_callback is callbacks.before_model
    assert ra.after_model_callback is callbacks.after_model
    assert ra.before_tool_callback is callbacks.before_tool
    assert ra.after_tool_callback is callbacks.after_tool


def test_root_agent_tem_o_toolset_mcp_e_instrucao_minima_em_pt_br():
    ra = agent.root_agent
    assert any(isinstance(t, mcp_conexao.McpToolset) for t in ra.tools)
    assert "Bússola" in ra.instruction
    assert "português" in ra.instruction.lower()
    assert "fonte" in ra.instruction.lower()  # cita a fonte (constituição III)


def test_montar_agente_inclui_ferramentas_e_instrucoes_das_extensoes():
    def criar_plano():
        return {}

    extensoes.registrar_ferramenta(criar_plano, sensivel=True)
    extensoes.registrar_instrucao(55, "Peça consentimento antes de criar o plano.")
    ra = agent.montar_agente()
    assert criar_plano in ra.tools
    assert "Peça consentimento antes de criar o plano." in ra.instruction


def test_modelo_vem_de_bussola_model():
    assert (
        agent.escolher_modelo({"BUSSOLA_MODEL": "gemini-x", "BUSSOLA_FAKES": "TRUE"}) == "gemini-x"
    )


def test_em_modo_fake_sem_modelo_usa_um_nome_de_teste():
    assert agent.escolher_modelo({"BUSSOLA_FAKES": "true"}) == agent.MODELO_DE_TESTE


def test_sem_modelo_e_sem_fakes_falha_apontando_o_smoke():
    with pytest.raises(RuntimeError, match="smoke_modelos"):
        agent.escolher_modelo({})
