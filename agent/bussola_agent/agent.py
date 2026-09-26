"""Agente hello da Bússola (ciclo 000). O ciclo 004 substitui este arquivo pelo agente real.

Mínimo de propósito: conecta ao MCP, instala os 4 callbacks agregados (cadeias vazias) e carrega as
extensões (005/006). Sem lógica de negócio, sem prompts de jornada.

`BUSSOLA_MODEL` vem do ambiente e é validado por `deploy/smoke_modelos.py`; sem ele (e sem
`BUSSOLA_FAKES=TRUE`) o agente não sobe, para não se inventar um ID de modelo.
"""

import os

from google.adk.agents import LlmAgent

from bussola_agent import callbacks, extensoes, mcp_conexao
from bussola_agent import logging_json as log

MODELO_DE_TESTE = "modelo-de-teste-nunca-enviado"

INSTRUCAO_BASE = (
    "Você é a Bússola, assistente financeira. Responda sempre em português do Brasil, com "
    "linguagem clara. Todo número que você citar deve vir de uma ferramenta e você deve dizer de "
    "qual fonte (ferramenta, tabela e período) ele veio; nunca calcule nem invente valores. "
    "Para perguntas sobre a situação financeira do cliente, use as ferramentas disponíveis."
)


def escolher_modelo(env=None) -> str:
    """ID do modelo: `BUSSOLA_MODEL`; em modo fake, um nome de teste; senão, erro explicativo."""
    env = os.environ if env is None else env
    if env.get("BUSSOLA_MODEL"):
        return env["BUSSOLA_MODEL"]
    if env.get("BUSSOLA_FAKES", "").strip().upper() == "TRUE":
        return MODELO_DE_TESTE
    raise RuntimeError(
        "BUSSOLA_MODEL não definido. Rode `uv run --project agent python deploy/smoke_modelos.py` "
        "para validar o ID do Gemini Flash e grave-o em contracts/env.example / no ambiente."
    )


def montar_agente() -> LlmAgent:
    """Monta o agente com as ferramentas e instruções registradas pelas extensões."""
    extensoes.carregar_extensoes()
    instrucao = "\n\n".join(t for t in (INSTRUCAO_BASE, extensoes.instrucoes()) if t)
    return LlmAgent(
        name="bussola",
        model=escolher_modelo(),
        instruction=instrucao,
        tools=[mcp_conexao.criar_toolset(), *extensoes.ferramentas()],
        before_model_callback=callbacks.before_model,
        after_model_callback=callbacks.after_model,
        before_tool_callback=callbacks.before_tool,
        after_tool_callback=callbacks.after_tool,
    )


log.configurar("bussola-agent")
root_agent = montar_agente()
