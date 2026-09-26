"""Chaves de `session.state` e enum da jornada (docs/ciclos/contratos.md §6).

Dono: ciclo 000. Quem escreve cada chave está em contratos §6 (004, 005 ou 006). Use `ler` e
`escrever` para o Python recusar chaves com erro de digitação.
"""

from enum import StrEnum

ID_USUARIO = "id_usuario"
ATE_ANOMES = "ate_anomes"
ESTADO_JORNADA = "estado_jornada"
OBJETIVO = "objetivo"
CENARIOS = "cenarios"
CENARIO_ESCOLHIDO = "cenario_escolhido"
ULTIMAS_FONTES = "ultimas_fontes"
CONSENTIMENTOS = "consentimentos"
PLANO_ID = "plano_id"
ACOMPANHAMENTO = "acompanhamento"

CHAVES = frozenset(
    {
        ID_USUARIO,
        ATE_ANOMES,
        ESTADO_JORNADA,
        OBJETIVO,
        CENARIOS,
        CENARIO_ESCOLHIDO,
        ULTIMAS_FONTES,
        CONSENTIMENTOS,
        PLANO_ID,
        ACOMPANHAMENTO,
    }
)


class EstadoJornada(StrEnum):
    OBJETIVO = "OBJETIVO"
    ENTENDER = "ENTENDER"
    ANTECIPAR = "ANTECIPAR"
    ORIENTAR = "ORIENTAR"
    AGIR = "AGIR"
    ACOMPANHAR = "ACOMPANHAR"


def _checar(chave: str) -> None:
    if chave not in CHAVES:
        raise ValueError(f"chave de session.state desconhecida: {chave!r}")


def ler(state, chave: str, padrao=None):
    """Lê `chave` de `state` (dict ou `State` do ADK); `padrao` se ausente."""
    _checar(chave)
    return state.get(chave, padrao)


def escrever(state, chave: str, valor) -> None:
    """Grava `valor` em `state[chave]`."""
    _checar(chave)
    state[chave] = valor
