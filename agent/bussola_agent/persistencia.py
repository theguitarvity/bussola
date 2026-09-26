"""Persistência de aplicação do agente (docs/ciclos/contratos.md §3 e §6).

`RegistroApp` é o contrato; `RegistroEmMemoria` é o fake do 000. O 005 entrega `RegistroBigQuery`
(`persistencia_bq.py`), que grava em `BQ_DATASET_APP` por streaming insert. Os modelos espelham as
colunas de `contracts/bigquery/bussola_app.sql` (o teste de contrato garante). Campos de id têm
padrão `""`: o registro gera um UUID quando o id vem vazio.
"""

import uuid
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, field_validator

DECISOES = ("aceito", "recusado")
TIPOS_EVENTO = (
    "sessao_iniciada",
    "estado_alterado",
    "ferramenta_chamada",
    "consentimento_solicitado",
    "consentimento_decidido",
    "plano_criado",
    "acao_executada",
    "guardrail_bloqueio",
    "acompanhamento_mes_avancado",
    "desvio_detectado",
    "rota_recalculada",
    "plano_ajustado",
)


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Plano(_Modelo):
    plano_id: str = ""
    session_id: str
    id_usuario: str
    objetivo: str
    valor_alvo: float
    prazo_meses: int
    cenario: str
    aporte_mensal: float
    ate_anomes: int
    criado_em: datetime


class Consentimento(_Modelo):
    consent_id: str = ""
    session_id: str
    plano_id: str | None = None
    acao: str
    decisao: str  # "aceito" | "recusado"
    texto_apresentado: str
    ts: datetime

    @field_validator("decisao")
    @classmethod
    def _decisao_valida(cls, valor: str) -> str:
        if valor not in DECISOES:
            raise ValueError(f"decisao deve ser uma de {DECISOES}")
        return valor


class EventoAuditoria(_Modelo):
    evento_id: str = ""
    session_id: str
    estado: str
    tipo_evento: str
    ferramenta: str | None = None
    resumo: dict[str, Any]
    ts: datetime

    @field_validator("tipo_evento")
    @classmethod
    def _tipo_valido(cls, valor: str) -> str:
        if valor not in TIPOS_EVENTO:
            raise ValueError(f"tipo_evento deve ser um de {TIPOS_EVENTO}")
        return valor


class Acompanhamento(_Modelo):
    plano_id: str
    anomes: int
    planejado: float
    realizado: float
    desvio: float
    categoria_desvio: str | None = None
    acao_sugerida: str | None = None
    ts: datetime


@runtime_checkable
class RegistroApp(Protocol):
    def registrar_plano(self, plano: Plano) -> str: ...

    def registrar_consentimento(self, c: Consentimento) -> str: ...

    def registrar_evento(self, e: EventoAuditoria) -> str: ...

    def registrar_acompanhamento(self, a: Acompanhamento) -> None: ...

    def obter_plano(self, plano_id: str) -> Plano | None: ...


class RegistroEmMemoria:
    """Fake de `RegistroApp`: guarda tudo em memória (nada é gravado em disco nem em BigQuery)."""

    def __init__(self) -> None:
        self._planos: dict[str, Plano] = {}
        self._consentimentos: list[Consentimento] = []
        self._eventos: list[EventoAuditoria] = []
        self._acompanhamentos: list[Acompanhamento] = []

    @property
    def consentimentos(self) -> list[Consentimento]:
        return list(self._consentimentos)

    @property
    def eventos(self) -> list[EventoAuditoria]:
        return list(self._eventos)

    @property
    def acompanhamentos(self) -> list[Acompanhamento]:
        return list(self._acompanhamentos)

    def registrar_plano(self, plano: Plano) -> str:
        plano = plano.model_copy(update={"plano_id": plano.plano_id or str(uuid.uuid4())})
        self._planos[plano.plano_id] = plano
        return plano.plano_id

    def registrar_consentimento(self, c: Consentimento) -> str:
        c = c.model_copy(update={"consent_id": c.consent_id or str(uuid.uuid4())})
        self._consentimentos.append(c)
        return c.consent_id

    def registrar_evento(self, e: EventoAuditoria) -> str:
        e = e.model_copy(update={"evento_id": e.evento_id or str(uuid.uuid4())})
        self._eventos.append(e)
        return e.evento_id

    def registrar_acompanhamento(self, a: Acompanhamento) -> None:
        self._acompanhamentos.append(a)

    def obter_plano(self, plano_id: str) -> Plano | None:
        return self._planos.get(plano_id)
