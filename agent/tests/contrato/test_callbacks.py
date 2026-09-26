"""Encadeador de callbacks (FR-012, AC8): ordem crescente, primeiro retorno não nulo interrompe."""

import pytest

from bussola_agent import callbacks as cb


@pytest.fixture(autouse=True)
def _cadeias_limpas():
    cb.limpar()
    yield
    cb.limpar()


# Argumentos que o ADK 2.10 passa, por nome, a cada fase (research R4).
ARGS = {
    "before_model": {"callback_context": "ctx", "llm_request": "req"},
    "after_model": {"callback_context": "ctx", "llm_response": "resp"},
    "before_tool": {"tool": "ferramenta", "args": {"a": 1}, "tool_context": "ctx"},
    "after_tool": {
        "tool": "ferramenta",
        "args": {"a": 1},
        "tool_context": "ctx",
        "tool_response": {"r": 1},
    },
}


def _agregado(fase: str):
    return getattr(cb, fase)


def test_as_quatro_fases():
    assert cb.FASES == ("before_model", "after_model", "before_tool", "after_tool")


@pytest.mark.parametrize("fase", cb.FASES)
async def test_ordem_10_que_retorna_valor_impede_a_ordem_20(fase):
    chamadas = []

    def ordem_20(**_):
        chamadas.append(20)
        return "vinte"

    def ordem_10(**_):
        chamadas.append(10)
        return "dez"

    cb.registrar(fase, ordem_20, 20)  # registrada primeiro, executa depois
    cb.registrar(fase, ordem_10, 10)
    assert await _agregado(fase)(**ARGS[fase]) == "dez"
    assert chamadas == [10]


@pytest.mark.parametrize("fase", cb.FASES)
async def test_retorno_none_continua_a_cadeia_em_ordem_crescente(fase):
    chamadas = []
    for ordem in (30, 10, 20):
        cb.registrar(fase, lambda ordem=ordem, **_: chamadas.append(ordem), ordem)
    assert await _agregado(fase)(**ARGS[fase]) is None
    assert chamadas == [10, 20, 30]


@pytest.mark.parametrize("fase", cb.FASES)
async def test_cadeia_vazia_devolve_none(fase):
    assert await _agregado(fase)(**ARGS[fase]) is None


async def test_empate_de_ordem_mantem_a_ordem_de_registro():
    chamadas = []
    for nome in ("a", "b", "c"):
        cb.registrar("before_model", lambda nome=nome, **_: chamadas.append(nome), 10)
    await cb.before_model(**ARGS["before_model"])
    assert chamadas == ["a", "b", "c"]


async def test_mistura_funcoes_sincronas_e_assincronas():
    chamadas = []

    async def assincrona(**_):
        chamadas.append("async")

    cb.registrar("after_tool", lambda **_: chamadas.append("sync"), 10)
    cb.registrar("after_tool", assincrona, 20)
    cb.registrar("after_tool", lambda **_: {"alterado": True}, 30)
    assert await cb.after_tool(**ARGS["after_tool"]) == {"alterado": True}
    assert chamadas == ["sync", "async"]


async def test_funcoes_recebem_os_argumentos_do_adk_por_nome():
    recebido = {}

    def antes_da_ferramenta(tool, args, tool_context):
        recebido.update(tool=tool, args=args, tool_context=tool_context)

    def depois_do_modelo(callback_context, llm_response):
        recebido.update(callback_context=callback_context, llm_response=llm_response)

    cb.registrar("before_tool", antes_da_ferramenta, 10)
    cb.registrar("after_model", depois_do_modelo, 10)
    await cb.before_tool(**ARGS["before_tool"])
    await cb.after_model(**ARGS["after_model"])
    assert recebido == {
        "tool": "ferramenta",
        "args": {"a": 1},
        "tool_context": "ctx",
        "callback_context": "ctx",
        "llm_response": "resp",
    }


async def test_excecao_dentro_de_uma_funcao_propaga():
    def quebrada(**_):
        raise RuntimeError("falhou")

    cb.registrar("before_model", quebrada, 10)
    with pytest.raises(RuntimeError, match="falhou"):
        await cb.before_model(**ARGS["before_model"])


def test_fase_invalida_e_recusada():
    with pytest.raises(ValueError, match="fase"):
        cb.registrar("during_model", lambda **_: None, 10)
