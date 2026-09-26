"""MCP mock do ciclo 000 (docs/ciclos/contratos.md §5 e §8). O ciclo 003 o substitui pelo real.

Serve as 7 ferramentas P0 e `resumo_mes` com as assinaturas exatas de §5, a partir das
fixtures: `ate_anomes == 202512` devolve o golden `__ate_202512`; qualquer corte anterior
devolve o golden `__ate_202506`, sempre com um aviso de mock. Os argumentos livres são
validados, mas não mudam o golden. Erros são o envelope `{"erro": {...}}` devolvido como
resultado (nunca exceção). A ordem de validação é: UUID -> `ate_anomes` -> argumentos da
ferramenta -> existência do usuário -> usuário-âncora.

As faixas são validadas aqui, no código, e não no schema, para virarem `ENTRADA_INVALIDA`
(research R2).
"""

import os
import re
import time
from collections.abc import Callable

from fastmcp import FastMCP

from bussola_mcp import contratos as c
from bussola_mcp import logging_json as log
from bussola_mcp.dominio import fakes

NOME = "bussola-mcp"
AVISO_MOCK = "Resposta de mock (ciclo 000): fixtures provisórias, não vêm da base real."
ANOMES_MIN, ANOMES_MAX = 202501, 202512
CORTE_INTERMEDIARIO = 202506
_UUID_V4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE
)

mcp = FastMCP(NOME)
_repositorio = fakes.RepositorioFake()
_buscador = fakes.BuscadorFake()
_ancora = next(u.id_usuario for u in fakes.usuarios() if u.papel == "ancora")

Erro = dict | None


def _erro(codigo: c.CodigoErro, mensagem: str) -> dict:
    return c.RespostaErro(erro=c.Erro(codigo=codigo, mensagem=mensagem)).model_dump(mode="json")


def _invalida(mensagem: str) -> dict:
    return _erro(c.CodigoErro.ENTRADA_INVALIDA, mensagem)


def _anomes_valido(valor) -> bool:
    return isinstance(valor, int) and ANOMES_MIN <= valor <= ANOMES_MAX and 1 <= valor % 100 <= 12


def _validar_escopo(id_usuario: str, ate_anomes: int) -> Erro:
    if not isinstance(id_usuario, str) or not _UUID_V4.match(id_usuario):
        return _invalida("id_usuario deve ser um UUID v4.")
    if not _anomes_valido(ate_anomes):
        return _invalida(f"ate_anomes deve estar entre {ANOMES_MIN} e {ANOMES_MAX}.")
    return None


def _validar_usuario(id_usuario: str) -> Erro:
    if not _repositorio.usuario_existe(id_usuario):
        return _erro(c.CodigoErro.USUARIO_INEXISTENTE, "Cliente não encontrado.")
    if id_usuario != _ancora:
        return _erro(c.CodigoErro.DADOS_INSUFICIENTES, "O mock só tem dados do usuário-âncora.")
    return None


def _resposta(envelope: dict) -> dict:
    """Acrescenta o aviso de mock, valida o envelope e o devolve como dict JSON."""
    envelope = {**envelope, "avisos": [*envelope.get("avisos", []), AVISO_MOCK]}
    return c.Resposta.model_validate(envelope).model_dump(mode="json")


def _golden(ferramenta: str, ate_anomes: int) -> dict:
    corte = ANOMES_MAX if ate_anomes == ANOMES_MAX else CORTE_INTERMEDIARIO
    return _resposta(fakes.golden(ferramenta, corte))


def _executar(
    ferramenta: str,
    id_usuario: str,
    ate_anomes: int,
    argumentos: Callable[[], Erro],
    responder: Callable[[], dict],
) -> dict:
    inicio = time.perf_counter()
    resultado = (
        _validar_escopo(id_usuario, ate_anomes)
        or argumentos()
        or _validar_usuario(id_usuario)
        or responder()
    )
    log.log_evento(
        "ferramenta_chamada",
        ferramenta=ferramenta,
        ate_anomes=ate_anomes if isinstance(ate_anomes, int) else None,
        latencia_ms=round((time.perf_counter() - inicio) * 1000),
        erro_codigo=resultado["erro"]["codigo"] if "erro" in resultado else None,
    )
    return resultado


def _sem_argumentos() -> Erro:
    return None


def _faixa(nome: str, valor, minimo: int, maximo: int) -> Erro:
    if not isinstance(valor, int) or not minimo <= valor <= maximo:
        return _invalida(f"{nome} deve estar entre {minimo} e {maximo}.")
    return None


def _positivo(nome: str, valor) -> Erro:
    if valor is None or valor <= 0:
        return _invalida(f"{nome} deve ser maior que zero.")
    return None


# --- ferramentas (assinaturas exatas de contratos §5) --------------------------------------------


@mcp.tool
def perfil_financeiro(id_usuario: str, ate_anomes: int) -> dict:
    """Perfil financeiro do cliente: renda, gasto, sobra, fontes de renda, saldo e série mensal."""
    return _executar(
        "perfil_financeiro",
        id_usuario,
        ate_anomes,
        _sem_argumentos,
        lambda: _golden("perfil_financeiro", ate_anomes),
    )


@mcp.tool
def capacidade_poupanca(id_usuario: str, ate_anomes: int) -> dict:
    """Capacidade mensal de poupança: sobra média/mediana, desvio padrão e meses negativos."""
    return _executar(
        "capacidade_poupanca",
        id_usuario,
        ate_anomes,
        _sem_argumentos,
        lambda: _golden("capacidade_poupanca", ate_anomes),
    )


@mcp.tool
def oportunidades_corte(id_usuario: str, ate_anomes: int, top_n: int = 5) -> dict:
    """Categorias discricionárias com maior economia potencial (top_n de 1 a 10)."""
    return _executar(
        "oportunidades_corte",
        id_usuario,
        ate_anomes,
        lambda: _faixa("top_n", top_n, 1, 10),
        lambda: _golden("oportunidades_corte", ate_anomes),
    )


@mcp.tool
def dividas_e_parcelas(id_usuario: str, ate_anomes: int) -> dict:
    """Parcelas ativas, juros pagos e comprometimento da renda."""
    return _executar(
        "dividas_e_parcelas",
        id_usuario,
        ate_anomes,
        _sem_argumentos,
        lambda: _golden("dividas_e_parcelas", ate_anomes),
    )


@mcp.tool
def simular_objetivo(
    id_usuario: str,
    ate_anomes: int,
    valor_alvo: float,
    prazo_meses: int | None = None,
    aporte_mensal: float | None = None,
    usar_saldo_atual: bool = False,
) -> dict:
    """Simula um objetivo: informe exatamente um entre prazo_meses (1-360) e aporte_mensal (> 0)."""

    def argumentos() -> Erro:
        if (prazo_meses is None) == (aporte_mensal is None):
            return _invalida("Informe exatamente um entre prazo_meses e aporte_mensal.")
        return (
            _positivo("valor_alvo", valor_alvo)
            or (_faixa("prazo_meses", prazo_meses, 1, 360) if prazo_meses is not None else None)
            or (_positivo("aporte_mensal", aporte_mensal) if aporte_mensal is not None else None)
        )

    return _executar(
        "simular_objetivo",
        id_usuario,
        ate_anomes,
        argumentos,
        lambda: _golden("simular_objetivo", ate_anomes),
    )


@mcp.tool
def comparar_cenarios(
    id_usuario: str, ate_anomes: int, valor_alvo: float, prazo_meses: int
) -> dict:
    """Compara os cenários conservador, equilibrado e acelerado (prazo_meses de 1 a 360)."""
    return _executar(
        "comparar_cenarios",
        id_usuario,
        ate_anomes,
        lambda: _positivo("valor_alvo", valor_alvo) or _faixa("prazo_meses", prazo_meses, 1, 360),
        lambda: _golden("comparar_cenarios", ate_anomes),
    )


@mcp.tool
def buscar_contexto_financeiro(id_usuario: str, ate_anomes: int, pergunta: str, k: int = 5) -> dict:
    """Busca trechos de contexto do próprio cliente (pergunta até 500 caracteres, k de 1 a 10)."""

    def argumentos() -> Erro:
        if not pergunta.strip() or len(pergunta) > 500:
            return _invalida("pergunta deve ter de 1 a 500 caracteres.")
        return _faixa("k", k, 1, 10)

    def responder() -> dict:
        trechos = _buscador.buscar(id_usuario, pergunta, k, ate_anomes)
        return _resposta(
            {
                "dados": {"trechos": [t.model_dump(mode="json") for t in trechos]},
                "fonte": {
                    "ferramenta": "buscar_contexto_financeiro",
                    "tabelas": ["bussola_rag.documentos"],
                    "periodo": {"inicio": ANOMES_MIN, "fim": ate_anomes},
                },
                "avisos": [],
            }
        )

    return _executar("buscar_contexto_financeiro", id_usuario, ate_anomes, argumentos, responder)


@mcp.tool
def resumo_mes(id_usuario: str, ate_anomes: int, anomes: int) -> dict:
    """Resumo de um mês (anomes <= ate_anomes): renda, gasto, sobra e gasto por macro."""

    def argumentos() -> Erro:
        if not _anomes_valido(anomes) or anomes > ate_anomes:
            return _invalida("anomes deve ser um AAAAMM válido, menor ou igual a ate_anomes.")
        return None

    return _executar(
        "resumo_mes",
        id_usuario,
        ate_anomes,
        argumentos,
        lambda: _resposta(fakes.resumo_mes(anomes)),
    )


def main() -> None:
    log.configurar(NOME)
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), path="/mcp")


if __name__ == "__main__":
    main()
