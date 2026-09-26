"""MCP mock (FR-018/019, AC5): 8 ferramentas, schema de contratos §5, golden e erros."""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from bussola_mcp import contratos as c
from bussola_mcp.dominio import fakes
from bussola_mcp.server import AVISO_MOCK, mcp

ANCORA = "36a21505-d6d4-42d3-b319-d51a133c7269"
CONTROLE = "31e94f2f-1463-49f9-a41a-b3f220ed976a"
DESCONHECIDO = "00000000-0000-4000-8000-000000000000"

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
COM_GOLDEN = [
    "perfil_financeiro",
    "capacidade_poupanca",
    "oportunidades_corte",
    "dividas_e_parcelas",
    "simular_objetivo",
    "comparar_cenarios",
]
ENTRADAS = fakes._json("ferramentas/_entradas.json")  # entradas válidas de cada golden

# Tabela literal de contratos §5:
# {ferramenta: (obrigatórios, {campo: tipos JSON}, {campo: padrão})}.
BASE = {"id_usuario": {"string"}, "ate_anomes": {"integer"}}
SCHEMA_5 = {
    "perfil_financeiro": ({"id_usuario", "ate_anomes"}, BASE, {}),
    "capacidade_poupanca": ({"id_usuario", "ate_anomes"}, BASE, {}),
    "dividas_e_parcelas": ({"id_usuario", "ate_anomes"}, BASE, {}),
    "oportunidades_corte": (
        {"id_usuario", "ate_anomes"},
        {**BASE, "top_n": {"integer"}},
        {"top_n": 5},
    ),
    "simular_objetivo": (
        {"id_usuario", "ate_anomes", "valor_alvo"},
        {
            **BASE,
            "valor_alvo": {"number"},
            "prazo_meses": {"integer", "null"},
            "aporte_mensal": {"number", "null"},
            "usar_saldo_atual": {"boolean"},
        },
        {"prazo_meses": None, "aporte_mensal": None, "usar_saldo_atual": False},
    ),
    "comparar_cenarios": (
        {"id_usuario", "ate_anomes", "valor_alvo", "prazo_meses"},
        {**BASE, "valor_alvo": {"number"}, "prazo_meses": {"integer"}},
        {},
    ),
    "buscar_contexto_financeiro": (
        {"id_usuario", "ate_anomes", "pergunta"},
        {**BASE, "pergunta": {"string"}, "k": {"integer"}},
        {"k": 5},
    ),
    "resumo_mes": (
        {"id_usuario", "ate_anomes", "anomes"},
        {**BASE, "anomes": {"integer"}},
        {},
    ),
}


def _args(ferramenta: str, **extra) -> dict:
    """Argumentos válidos para o âncora (ate_anomes = 202506 por padrão)."""
    base = {"id_usuario": ANCORA, "ate_anomes": 202506}
    especificos = {
        "oportunidades_corte": ENTRADAS["oportunidades_corte"],
        "simular_objetivo": ENTRADAS["simular_objetivo"],
        "comparar_cenarios": ENTRADAS["comparar_cenarios"],
        "buscar_contexto_financeiro": ENTRADAS["buscar_contexto_financeiro"],
        "resumo_mes": {"anomes": 202503},
    }.get(ferramenta, {})
    return {**base, **especificos, **extra}


async def _chamar(ferramenta: str, **extra) -> dict:
    async with Client(mcp) as cliente:
        return (await cliente.call_tool(ferramenta, _args(ferramenta, **extra))).data


def _codigo(resposta: dict) -> str:
    return resposta["erro"]["codigo"]


def _tipos(propriedade: dict) -> set[str]:
    if "type" in propriedade:
        return {propriedade["type"]}
    return {alternativa["type"] for alternativa in propriedade["anyOf"]}


# --- lista e schema -----------------------------------------------------------------------------


async def test_lista_exatamente_as_8_ferramentas():
    async with Client(mcp) as cliente:
        assert {t.name for t in await cliente.list_tools()} == FERRAMENTAS
    assert set(c.FERRAMENTAS_MOCK) == FERRAMENTAS


async def test_schema_das_ferramentas_bate_com_contratos_5_e_com_os_modelos():
    async with Client(mcp) as cliente:
        ferramentas = {t.name: t.input_schema for t in await cliente.list_tools()}
    for nome, (obrigatorios, campos, padroes) in SCHEMA_5.items():
        schema = ferramentas[nome]
        propriedades = schema["properties"]
        assert set(propriedades) == set(campos), nome
        assert set(schema.get("required", [])) == obrigatorios, nome
        for campo, tipos in campos.items():
            assert _tipos(propriedades[campo]) == tipos, (nome, campo)
        for campo, padrao in padroes.items():
            assert propriedades[campo].get("default") == padrao, (nome, campo)
        assert set(propriedades) == set(c.FERRAMENTAS[nome][0].model_fields), nome


# --- golden por corte ---------------------------------------------------------------------------


@pytest.mark.parametrize(("ate", "corte"), [(202506, 202506), (202512, 202512), (202503, 202506)])
@pytest.mark.parametrize("ferramenta", COM_GOLDEN)
async def test_devolve_o_golden_do_corte_com_aviso_de_mock(ferramenta, ate, corte):
    resposta = await _chamar(ferramenta, ate_anomes=ate)
    esperado = fakes.golden(ferramenta, corte)
    assert resposta["dados"] == esperado["dados"]
    assert resposta["fonte"] == esperado["fonte"]
    assert resposta["avisos"] == [*esperado["avisos"], AVISO_MOCK]
    c.Resposta.model_validate(resposta)
    c.FERRAMENTAS[ferramenta][1].model_validate(resposta["dados"])


async def test_argumentos_livres_sao_validados_mas_nao_mudam_o_golden():
    padrao = await _chamar("oportunidades_corte")
    outro = await _chamar("oportunidades_corte", top_n=1)
    assert outro["dados"] == padrao["dados"]


async def test_buscar_contexto_so_devolve_trechos_do_proprio_usuario_ou_coorte():
    resposta = await _chamar("buscar_contexto_financeiro", ate_anomes=202512, k=10)
    trechos = c.DadosBuscarContexto.model_validate(resposta["dados"]).trechos
    assert trechos
    assert {t.origem.id_usuario for t in trechos} <= {ANCORA, None}
    assert AVISO_MOCK in resposta["avisos"]
    assert resposta["fonte"]["tabelas"] == ["bussola_rag.documentos"]


async def test_resumo_mes_devolve_o_arquivo_do_mes():
    resposta = await _chamar("resumo_mes", anomes=202503)
    esperado = fakes.resumo_mes(202503)
    assert resposta["dados"] == esperado["dados"]
    assert resposta["avisos"] == [*esperado["avisos"], AVISO_MOCK]


# --- erros como envelope ------------------------------------------------------------------------


@pytest.mark.parametrize("ferramenta", sorted(FERRAMENTAS))
async def test_uuid_desconhecido_e_usuario_inexistente(ferramenta):
    resposta = await _chamar(ferramenta, id_usuario=DESCONHECIDO)
    assert _codigo(resposta) == "USUARIO_INEXISTENTE"
    c.RespostaErro.model_validate(resposta)


@pytest.mark.parametrize("ferramenta", sorted(FERRAMENTAS))
@pytest.mark.parametrize("malformado", ["nao-e-uuid", "", "36a21505-d6d4-12d3-b319-d51a133c7269"])
async def test_uuid_malformado_e_entrada_invalida(ferramenta, malformado):
    assert _codigo(await _chamar(ferramenta, id_usuario=malformado)) == "ENTRADA_INVALIDA"


@pytest.mark.parametrize("ferramenta", sorted(FERRAMENTAS))
@pytest.mark.parametrize("ate", [202601, 202412, 202513, 202500, 0])
async def test_ate_anomes_fora_de_202501_202512_e_entrada_invalida(ferramenta, ate):
    assert _codigo(await _chamar(ferramenta, ate_anomes=ate)) == "ENTRADA_INVALIDA"


async def test_usuario_de_controle_nao_recebe_dado_do_ancora():
    for ferramenta in sorted(FERRAMENTAS):
        resposta = await _chamar(ferramenta, id_usuario=CONTROLE)
        assert _codigo(resposta) == "DADOS_INSUFICIENTES", ferramenta
        assert "dados" not in resposta


@pytest.mark.parametrize(
    ("ferramenta", "extra"),
    [
        ("simular_objetivo", {"prazo_meses": 36, "aporte_mensal": 1500.0}),  # os dois juntos
        ("simular_objetivo", {"prazo_meses": None, "aporte_mensal": None}),  # nenhum dos dois
        ("simular_objetivo", {"prazo_meses": 0, "aporte_mensal": None}),
        ("simular_objetivo", {"prazo_meses": 361, "aporte_mensal": None}),
        ("simular_objetivo", {"prazo_meses": None, "aporte_mensal": 0.0}),
        ("simular_objetivo", {"valor_alvo": 0.0}),
        ("simular_objetivo", {"valor_alvo": -1.0}),
        ("comparar_cenarios", {"valor_alvo": 0.0}),
        ("comparar_cenarios", {"prazo_meses": 0}),
        ("comparar_cenarios", {"prazo_meses": 361}),
        ("oportunidades_corte", {"top_n": 0}),
        ("oportunidades_corte", {"top_n": 11}),
        ("buscar_contexto_financeiro", {"k": 0}),
        ("buscar_contexto_financeiro", {"k": 11}),
        ("buscar_contexto_financeiro", {"pergunta": "x" * 501}),
        ("buscar_contexto_financeiro", {"pergunta": "   "}),
        ("resumo_mes", {"anomes": 202507}),  # > ate_anomes (202506)
        ("resumo_mes", {"anomes": 202412}),
    ],
)
async def test_argumentos_da_ferramenta_fora_da_faixa_sao_entrada_invalida(ferramenta, extra):
    assert _codigo(await _chamar(ferramenta, **extra)) == "ENTRADA_INVALIDA"


@pytest.mark.parametrize(
    ("ferramenta", "extra"),
    [
        ("simular_objetivo", {"prazo_meses": 1, "aporte_mensal": None}),
        ("simular_objetivo", {"prazo_meses": 360, "aporte_mensal": None}),
        ("simular_objetivo", {"prazo_meses": None, "aporte_mensal": 1500.0}),
        ("comparar_cenarios", {"prazo_meses": 360}),
        ("oportunidades_corte", {"top_n": 10}),
        ("buscar_contexto_financeiro", {"k": 10, "pergunta": "x" * 500}),
    ],
)
async def test_limites_validos_passam(ferramenta, extra):
    assert "erro" not in await _chamar(ferramenta, **extra)


async def test_tipo_errado_e_recusado_pelo_protocolo_antes_do_envelope():
    """O FastMCP valida tipos simples por conta própria (research R2)."""
    async with Client(mcp) as cliente:
        with pytest.raises(ToolError):
            await cliente.call_tool(
                "perfil_financeiro", {"id_usuario": ANCORA, "ate_anomes": "abc"}
            )
