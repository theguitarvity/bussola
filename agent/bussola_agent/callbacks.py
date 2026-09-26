"""Encadeador de callbacks do ADK (docs/ciclos/contratos.md §6).

O `agent.py` instala só os 4 callbacks agregados abaixo. Cada ciclo registra suas funções com
`registrar(fase, funcao, ordem)`. A cadeia roda em ordem crescente (empate: ordem de registro) e o
primeiro retorno não nulo interrompe. Uma exceção dentro de uma função propaga.

O ADK 2.10 chama os callbacks por NOME de argumento, e as funções registradas são chamadas do
mesmo jeito (por nome), então têm estas assinaturas (síncronas ou assíncronas):

    before_model(callback_context, llm_request)
    after_model(callback_context, llm_response)
    before_tool(tool, args, tool_context)
    after_tool(tool, args, tool_context, tool_response)

Ordens reservadas (contratos §6): before_model 10/20 (005); before_tool 10 (004), 20 (005),
90 (005); after_tool 10 (004), 90 (005); after_model 10 (005), 50 (004).
"""

import inspect
import itertools
from collections.abc import Callable

FASES = ("before_model", "after_model", "before_tool", "after_tool")

_cadeias: dict[str, list[tuple[int, int, Callable]]] = {fase: [] for fase in FASES}
_sequencia = itertools.count()


def registrar(fase: str, funcao: Callable, ordem: int) -> None:
    """Acrescenta `funcao` à cadeia de `fase` com a `ordem` dada."""
    if fase not in _cadeias:
        raise ValueError(f"fase desconhecida: {fase!r} (use uma de {FASES})")
    _cadeias[fase].append((ordem, next(_sequencia), funcao))
    _cadeias[fase].sort(key=lambda item: (item[0], item[1]))


def limpar() -> None:
    """Esvazia as 4 cadeias (uso em testes)."""
    for cadeia in _cadeias.values():
        cadeia.clear()


async def _executar(fase: str, **argumentos):
    for _ordem, _seq, funcao in list(_cadeias[fase]):
        resultado = funcao(**argumentos)
        if inspect.isawaitable(resultado):
            resultado = await resultado
        if resultado is not None:
            return resultado
    return None


async def before_model(callback_context, llm_request):
    return await _executar(
        "before_model", callback_context=callback_context, llm_request=llm_request
    )


async def after_model(callback_context, llm_response):
    return await _executar(
        "after_model", callback_context=callback_context, llm_response=llm_response
    )


async def before_tool(tool, args, tool_context):
    return await _executar("before_tool", tool=tool, args=args, tool_context=tool_context)


async def after_tool(tool, args, tool_context, tool_response):
    return await _executar(
        "after_tool", tool=tool, args=args, tool_context=tool_context, tool_response=tool_response
    )
