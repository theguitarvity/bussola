"""Conexão MCP do agente (FR-015, AC6): o MCPToolset lista as ferramentas do mock local, sem LLM."""

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from bussola_agent import mcp_conexao as mc

RAIZ = Path(__file__).resolve().parents[3]
ANCORA = "36a21505-d6d4-42d3-b319-d51a133c7269"
FERRAMENTAS = {
    "perfil_financeiro",
    "capacidade_poupanca",
    "oportunidades_corte",
    "dividas_e_parcelas",
    "simular_objetivo",
    "comparar_cenarios",
    "buscar_contexto_financeiro",
    "resumo_mes",
}


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def url_mock():
    """Sobe o MCP mock (projeto mcp_server) numa porta livre de localhost e o derruba no fim."""
    porta = _porta_livre()
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env.update(PORT=str(porta), BUSSOLA_FAKES="TRUE")
    processo = subprocess.Popen(
        ["uv", "run", "--frozen", "python", "-m", "bussola_mcp.server"],
        cwd=RAIZ / "mcp_server",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        limite = time.monotonic() + 60
        while True:
            if processo.poll() is not None:
                pytest.fail("o mock encerrou antes de subir")
            try:
                with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
                    break
            except OSError:
                if time.monotonic() > limite:
                    pytest.fail("o mock não subiu em 60 s")
                time.sleep(0.2)
        yield f"http://127.0.0.1:{porta}/mcp"
    finally:
        processo.terminate()
        try:
            processo.wait(10)
        except subprocess.TimeoutExpired:
            processo.kill()


async def test_toolset_conecta_no_mock_e_lista_as_8_ferramentas_sem_llm(url_mock):
    toolset = mc.criar_toolset(url=url_mock)
    try:
        assert {t.name for t in await toolset.get_tools()} == FERRAMENTAS
    finally:
        await toolset.close()


async def test_chamar_ferramenta_forca_id_usuario_e_ate_anomes_do_state(url_mock, monkeypatch):
    monkeypatch.setenv("MCP_URL", url_mock)
    state = {"id_usuario": ANCORA, "ate_anomes": 202512}
    # o modelo tenta outro usuário e outro corte: o escopo vem do state
    resposta = await mc.chamar_ferramenta(
        "perfil_financeiro", {"id_usuario": "quero-outro-usuario", "ate_anomes": 202501}, state
    )
    assert "erro" not in resposta
    assert resposta["fonte"]["periodo"] == {"inicio": 202501, "fim": 202512}


async def test_argumentos_extras_passam_e_erro_do_servidor_volta_como_envelope(
    url_mock, monkeypatch
):
    monkeypatch.setenv("MCP_URL", url_mock)
    state = {"id_usuario": ANCORA, "ate_anomes": 202506}
    ok = await mc.chamar_ferramenta("resumo_mes", {"anomes": 202503}, state)
    assert ok["dados"]["anomes"] == 202503
    erro = await mc.chamar_ferramenta("resumo_mes", {"anomes": 202601}, state)
    assert erro["erro"]["codigo"] == "ENTRADA_INVALIDA"


async def test_tipo_errado_recusado_pelo_protocolo_volta_como_envelope_nunca_none(
    url_mock, monkeypatch
):
    monkeypatch.setenv("MCP_URL", url_mock)
    state = {"id_usuario": ANCORA, "ate_anomes": 202506}
    resposta = await mc.chamar_ferramenta("oportunidades_corte", {"top_n": "abc"}, state)
    assert resposta["erro"]["codigo"] == "ENTRADA_INVALIDA"


async def test_ferramenta_inexistente_volta_como_envelope(url_mock, monkeypatch):
    monkeypatch.setenv("MCP_URL", url_mock)
    state = {"id_usuario": ANCORA, "ate_anomes": 202506}
    resposta = await mc.chamar_ferramenta("nao_existe", {}, state)
    assert resposta["erro"]["codigo"] in ("ENTRADA_INVALIDA", "INDISPONIVEL")


@pytest.mark.parametrize("state", [{}, {"id_usuario": ANCORA}, {"ate_anomes": 202506}])
async def test_state_sem_o_escopo_devolve_erro_local_sem_chamar_o_servidor(state, monkeypatch):
    monkeypatch.setenv(
        "MCP_URL", "http://127.0.0.1:1/mcp"
    )  # se tentasse conectar, daria INDISPONIVEL
    resposta = await mc.chamar_ferramenta("perfil_financeiro", {}, state)
    assert resposta["erro"]["codigo"] == "ENTRADA_INVALIDA"


async def test_servidor_indisponivel_vira_envelope_indisponivel(monkeypatch):
    monkeypatch.setenv("MCP_URL", f"http://127.0.0.1:{_porta_livre()}/mcp")
    state = {"id_usuario": ANCORA, "ate_anomes": 202506}
    resposta = await mc.chamar_ferramenta("perfil_financeiro", {}, state)
    assert resposta["erro"]["codigo"] == "INDISPONIVEL"


def test_url_e_oidc_vem_do_ambiente(monkeypatch):
    monkeypatch.delenv("MCP_URL", raising=False)
    monkeypatch.delenv("MCP_USE_OIDC", raising=False)
    assert mc.mcp_url() == "http://localhost:8080/mcp"
    assert mc.usa_oidc() is False
    monkeypatch.setenv("MCP_URL", "https://bussola-mcp-abc.us-central1.run.app/mcp")
    monkeypatch.setenv("MCP_USE_OIDC", "true")
    assert mc.mcp_url() == "https://bussola-mcp-abc.us-central1.run.app/mcp"
    assert mc.usa_oidc() is True


def test_audience_e_a_url_base_do_mcp():
    assert (
        mc.audience("https://bussola-mcp-abc.us-central1.run.app/mcp")
        == "https://bussola-mcp-abc.us-central1.run.app"
    )


async def test_cabecalhos_oidc_devolvem_bearer_com_o_id_token_da_audience(monkeypatch):
    pedidos = []

    def fetch(_request, audience):
        pedidos.append(audience)
        return f"token-para-{audience}"

    monkeypatch.setattr(mc, "fetch_id_token", fetch)
    mc._cache_tokens.clear()
    provider = mc.cabecalhos_oidc("https://mcp.exemplo.app/mcp")
    assert await provider(None) == {"Authorization": "Bearer token-para-https://mcp.exemplo.app"}
    await provider(None)
    assert pedidos == ["https://mcp.exemplo.app"]  # o token é reaproveitado (cache curto)


def test_criar_toolset_so_usa_header_provider_com_oidc(monkeypatch):
    capturado = {}

    class ToolsetFalso:
        def __init__(self, **kwargs):
            capturado.update(kwargs)

    monkeypatch.setattr(mc, "McpToolset", ToolsetFalso)
    monkeypatch.setenv("MCP_URL", "http://localhost:8080/mcp")
    monkeypatch.setenv("MCP_USE_OIDC", "FALSE")
    mc.criar_toolset()
    assert capturado["header_provider"] is None
    assert capturado["connection_params"].url == "http://localhost:8080/mcp"
    monkeypatch.setenv("MCP_USE_OIDC", "TRUE")
    mc.criar_toolset()
    assert callable(capturado["header_provider"])
