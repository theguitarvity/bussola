"""Conexão do agente com o `bussola-mcp` (docs/ciclos/contratos.md §6).

`criar_toolset()` devolve o `MCPToolset` do ADK (streamable HTTP); com `MCP_USE_OIDC=TRUE` cada
chamada leva `Authorization: Bearer <ID token>` com `audience` = URL base do MCP (research R3).
`chamar_ferramenta()` chama uma ferramenta direto, sem passar pelo LLM, sempre com `id_usuario` e
`ate_anomes` forçados a partir do `state` (o mesmo escopo do callback do 004).

Limite: `fetch_id_token` só funciona com service account ou com o metadata server (Cloud Run); com
ADC de usuário, use `MCP_USE_OIDC=FALSE` local.
"""

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import httpx2
import mcp
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.auth.transport.requests import Request
from google.oauth2.id_token import fetch_id_token
from mcp.client.streamable_http import streamable_http_client

from bussola_agent import estado
from bussola_agent import logging_json as log

URL_PADRAO = "http://localhost:8080/mcp"
TTL_TOKEN_SEGUNDOS = 50 * 60  # ID tokens do Google duram ~1 h

_cache_tokens: dict[str, tuple[float, str]] = {}


def mcp_url() -> str:
    return os.environ.get("MCP_URL") or URL_PADRAO


def usa_oidc() -> bool:
    return os.environ.get("MCP_USE_OIDC", "FALSE").strip().upper() == "TRUE"


def audience(url: str) -> str:
    """URL base (esquema + host) do serviço, usada como `audience` do ID token."""
    partes = urlsplit(url)
    return f"{partes.scheme}://{partes.netloc}"


def _obter_id_token(aud: str) -> str:
    vencimento, token = _cache_tokens.get(aud, (0.0, ""))
    if time.monotonic() >= vencimento:
        token = fetch_id_token(Request(), aud)
        _cache_tokens[aud] = (time.monotonic() + TTL_TOKEN_SEGUNDOS, token)
    return token


def cabecalhos_oidc(url: str) -> Callable[[object], Awaitable[dict[str, str]]]:
    """`header_provider` do ADK: cabeçalho Bearer com o ID token da audience de `url`."""
    aud = audience(url)

    async def provider(_readonly_context) -> dict[str, str]:
        token = await asyncio.to_thread(_obter_id_token, aud)
        return {"Authorization": f"Bearer {token}"}

    return provider


def criar_toolset(url: str | None = None) -> McpToolset:
    """`MCPToolset` apontando para `url` (padrão `MCP_URL`)."""
    url = url or mcp_url()
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=url),
        header_provider=cabecalhos_oidc(url) if usa_oidc() else None,
    )


def _erro(codigo: str, mensagem: str) -> dict:
    return {"erro": {"codigo": codigo, "mensagem": mensagem}}


async def chamar_ferramenta(nome: str, args: dict, state) -> dict:
    """Chama a ferramenta MCP `nome` sem LLM, com o escopo (`id_usuario`, `ate_anomes`) do `state`.

    Devolve o envelope do servidor (sucesso ou `{"erro": ...}`). Sem escopo no `state` devolve
    `ENTRADA_INVALIDA` local, sem contatar o servidor; falha de conexão vira `INDISPONIVEL`.
    """
    id_usuario = estado.ler(state, estado.ID_USUARIO)
    ate_anomes = estado.ler(state, estado.ATE_ANOMES)
    if not id_usuario or ate_anomes is None:
        return _erro("ENTRADA_INVALIDA", "id_usuario e ate_anomes precisam estar no session.state.")
    argumentos = {**args, "id_usuario": id_usuario, "ate_anomes": ate_anomes}
    url = mcp_url()
    inicio = time.perf_counter()
    try:
        cabecalhos = {}
        if usa_oidc():
            cabecalhos = await cabecalhos_oidc(url)(None)
        transporte = streamable_http_client(url, http_client=httpx2.AsyncClient(headers=cabecalhos))
        async with mcp.Client(transporte) as cliente:
            resultado = await cliente.call_tool(nome, argumentos)
    except Exception:  # fronteira de serviço: o agente não deve cair se o MCP estiver fora
        log.log_evento(
            "mcp_indisponivel",
            ferramenta=nome,
            ate_anomes=ate_anomes,
            latencia_ms=round((time.perf_counter() - inicio) * 1000),
            erro_codigo="INDISPONIVEL",
        )
        return _erro("INDISPONIVEL", "Serviço de dados indisponível no momento.")
    if resultado.structured_content is None:
        # o servidor recusou antes de a ferramenta rodar (ex.: tipo errado) ou não devolveu dados
        if getattr(resultado, "is_error", False):
            return _erro("ENTRADA_INVALIDA", "O serviço de dados recusou os argumentos.")
        return _erro("INDISPONIVEL", "Resposta inválida do serviço de dados.")
    return resultado.structured_content
