"""Registro de extensões: permite que 005 e 006 acrescentem comportamento sem editar o agent.py.

Contratos §6. `carregar_extensoes()` importa `bussola_agent.governanca` (005) e
`bussola_agent.acompanhamento` (006) quando existirem; o `__init__.py` de cada pacote registra suas
ferramentas, instruções e callbacks. Ignora só a AUSÊNCIA do pacote: qualquer erro dentro de um
pacote presente (inclusive `ImportError` de um módulo que ele importa) propaga.

Faixas de ordem de instrução reservadas: 004 usa 0-49, 005 usa 50-69, 006 usa 70-89 (convenção,
sem enforcement).
"""

import importlib
import itertools
from collections.abc import Callable

PACOTES = ("bussola_agent.governanca", "bussola_agent.acompanhamento")
FAIXAS_INSTRUCAO = {"004": (0, 49), "005": (50, 69), "006": (70, 89)}

_ferramentas: list[Callable] = []
_sensiveis: set[str] = set()
_instrucoes: list[tuple[int, int, str]] = []
_sequencia = itertools.count()


def registrar_ferramenta(fn: Callable, sensivel: bool = False) -> None:
    """Registra uma ferramenta ADK local. `sensivel=True` exige consentimento (gate do 005)."""
    if fn not in _ferramentas:
        _ferramentas.append(fn)
    if sensivel:
        _sensiveis.add(fn.__name__)


def registrar_instrucao(ordem: int, texto: str) -> None:
    """Registra um trecho do prompt; os trechos são concatenados por `ordem` crescente."""
    _instrucoes.append((ordem, next(_sequencia), texto))


def ferramentas() -> list[Callable]:
    return list(_ferramentas)


def sensiveis() -> set[str]:
    """Nomes das ferramentas registradas como sensíveis."""
    return set(_sensiveis)


def instrucoes() -> str:
    return "\n\n".join(texto for _ordem, _seq, texto in sorted(_instrucoes))


def limpar() -> None:
    """Esvazia o registro (uso em testes)."""
    _ferramentas.clear()
    _sensiveis.clear()
    _instrucoes.clear()


def carregar_extensoes() -> None:
    """Importa os pacotes de extensão que existirem; ignora os que não existem."""
    for pacote in PACOTES:
        try:
            importlib.import_module(pacote)
        except ModuleNotFoundError as erro:
            ausente = erro.name or ""
            if not (pacote == ausente or pacote.startswith(ausente + ".")):
                raise
