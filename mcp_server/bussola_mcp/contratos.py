"""Contratos v1 em código: modelos de I/O do MCP (docs/ciclos/contratos.md §3 e §5).

Dono: ciclo 000. Só muda por PR `contracts:` (contratos §0). Os modelos de linha espelham as colunas
do DDL em `contracts/bigquery/` (o teste de contrato garante); os modelos `Entrada*` e `Dados*`
espelham a tabela de ferramentas de §5. Valores monetários são `float` em BRL (2 casas nas saídas).
As faixas de valores (UUID, `ate_anomes`, `top_n`...) são validadas no servidor, que devolve o
envelope de erro; por isso os campos aqui são de tipo simples (research.md R2).
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- códigos de erro e envelopes (§5) ---------------------------------------------------------


class CodigoErro(StrEnum):
    """Códigos de erro do MCP.

    `CONSENTIMENTO_NECESSARIO`, `SEM_PLANO_ATIVO` e `FIM_DO_REPLAY` são locais do agente.
    """

    USUARIO_INEXISTENTE = "USUARIO_INEXISTENTE"
    ENTRADA_INVALIDA = "ENTRADA_INVALIDA"
    PRAZO_IMPLAUSIVEL = "PRAZO_IMPLAUSIVEL"
    DADOS_INSUFICIENTES = "DADOS_INSUFICIENTES"
    INDISPONIVEL = "INDISPONIVEL"


class Periodo(_Modelo):
    inicio: int
    fim: int


class Fonte(_Modelo):
    """Origem dos números: só `dataset.tabela`, nunca SQL, projeto ou credencial."""

    ferramenta: str
    tabelas: list[str]
    periodo: Periodo


class Erro(_Modelo):
    codigo: CodigoErro
    mensagem: str


class Resposta(_Modelo):
    """Envelope de sucesso."""

    dados: dict[str, Any]
    fonte: Fonte
    avisos: list[str] = Field(default_factory=list)


class RespostaErro(_Modelo):
    """Envelope de erro: é o resultado da ferramenta, não uma exceção."""

    erro: Erro


# --- linhas de bussola_dados (§3) -------------------------------------------------------------


class PerfilMes(_Modelo):
    id_usuario: str
    anomes: int
    renda: float
    gasto: float
    sobra: float
    saldo_inicial: float
    saldo_final: float
    saldo_minimo: float
    saldo_maximo: float
    juros: float


class GastoCategoria(_Modelo):
    id_usuario: str
    anomes: int
    macro: str
    micro: str
    total: float
    qtd: int


class EntradaCategoria(_Modelo):
    id_usuario: str
    anomes: int
    macro: str
    micro: str
    total: float
    qtd: int


class Recorrente(_Modelo):
    id_usuario: str
    anomes: int
    descr_norm: str
    macro: str
    micro: str
    valor: float


class Parcela(_Modelo):
    id_usuario: str
    anomes: int
    descr: str
    macro: str
    parcela_atual: int
    parcela_total: int
    vlr: float


class Categoria(_Modelo):
    macro: str
    micro: str
    discricionaria: bool
    corte_max_pct: float


class RefCoorte(_Modelo):
    faixa_renda: str
    macro: str
    media: float
    mediana: float
    qtd_usuarios: int


# --- linha de bussola_rag (§3) e trecho devolvido pela busca (§5) ------------------------------


class Documento(_Modelo):
    doc_id: str
    id_usuario: str | None
    tipo: str
    anomes: int | None
    texto: str
    fonte: dict[str, Any]
    embedding: list[float] = Field(default_factory=list)
    modelo_embedding: str
    gerado_em: datetime


class OrigemTrecho(_Modelo):
    id_usuario: str | None = None
    anomes: int | None = None
    categoria: str | None = None


class Trecho(_Modelo):
    doc_id: str
    tipo: str
    anomes: int | None
    texto: str
    score: float
    origem: OrigemTrecho


# --- fixtures ---------------------------------------------------------------------------------


class UsuarioFixture(_Modelo):
    """Linha de `contracts/fixtures/usuarios.json`. `origem` é campo opcional novo (Q-004)."""

    id_usuario: str
    papel: str  # "ancora" | "controle"
    origem: str = "base_real"  # "base_real" | "sintetico_teste"


# --- entrada de cada ferramenta (§5); id_usuario e ate_anomes são comuns e obrigatórios ---------


class EntradaBase(_Modelo):
    id_usuario: str
    ate_anomes: int


class EntradaPerfilFinanceiro(EntradaBase):
    pass


class EntradaCapacidadePoupanca(EntradaBase):
    pass


class EntradaDividasParcelas(EntradaBase):
    pass


class EntradaOportunidadesCorte(EntradaBase):
    top_n: int = 5  # 1-10


class EntradaSimularObjetivo(EntradaBase):
    valor_alvo: float  # > 0
    prazo_meses: int | None = None  # 1-360; exatamente um entre prazo_meses e aporte_mensal
    aporte_mensal: float | None = None  # > 0
    usar_saldo_atual: bool = False


class EntradaCompararCenarios(EntradaBase):
    valor_alvo: float  # > 0
    prazo_meses: int  # 1-360


class EntradaBuscarContexto(EntradaBase):
    pergunta: str  # até 500 caracteres
    k: int = 5  # 1-10


class EntradaResumoMes(EntradaBase):
    anomes: int  # <= ate_anomes


class EntradaReferenciaCoorte(EntradaBase):
    categoria: str  # macro


# --- campo `dados` de cada ferramenta (§5) ----------------------------------------------------


class FonteRenda(_Modelo):
    macro: str
    micro: str
    media: float


class SaldoResumo(_Modelo):
    minimo: float
    maximo: float
    atual: float


class PontoSerie(_Modelo):
    anomes: int
    renda: float
    gasto: float
    sobra: float


class DadosPerfilFinanceiro(_Modelo):
    renda_media: float
    gasto_medio: float
    sobra_media: float
    sobra_mediana: float
    fontes_renda: list[FonteRenda]
    saldo: SaldoResumo
    serie_mensal: list[PontoSerie]
    meses_considerados: int


class DadosCapacidadePoupanca(_Modelo):
    sobra_media: float
    sobra_mediana: float
    desvio_padrao: float
    meses_negativos: int
    meses_considerados: int


class CategoriaCorte(_Modelo):
    macro: str
    micro: str
    media_mensal: float
    discricionaria: bool
    economia_potencial_mensal: float
    criterio: str


class DadosOportunidadesCorte(_Modelo):
    categorias: list[CategoriaCorte]


class ParcelaAtiva(_Modelo):
    descr: str
    parcela_atual: int
    parcela_total: int
    valor: float
    meses_restantes: int


class DadosDividasParcelas(_Modelo):
    parcelas_ativas: list[ParcelaAtiva]
    juros_pagos_media: float
    comprometimento_renda_pct: float


class DadosSimularObjetivo(_Modelo):
    modo: str  # "prazo" | "aporte"
    valor_alvo: float
    aporte_mensal: float
    prazo_meses: int
    viavel: bool
    folga_mensal: float
    premissas: dict[str, Any]


class CorteSugerido(_Modelo):
    macro: str
    micro: str
    valor_mensal: float


class Cenario(_Modelo):
    nome: str
    pct_capacidade: float
    aporte_mensal: float
    prazo_meses: int
    viavel: bool
    cortes_sugeridos: list[CorteSugerido]
    trade_offs: list[str]


class DadosCompararCenarios(_Modelo):
    cenarios: list[Cenario]
    regras: dict[str, Any]


class DadosBuscarContexto(_Modelo):
    trechos: list[Trecho]


class GastoMacro(_Modelo):
    macro: str
    total: float


class DadosResumoMes(_Modelo):
    anomes: int
    renda: float
    gasto: float
    sobra: float
    gastos_macro: list[GastoMacro]


class DadosReferenciaCoorte(_Modelo):
    faixa_renda: str
    macro: str
    media: float
    mediana: float
    qtd_usuarios: int


# --- catálogo: nome da ferramenta -> (modelo de entrada, modelo de `dados`) ---------------------

FERRAMENTAS: dict[str, tuple[type[EntradaBase], type[_Modelo]]] = {
    "perfil_financeiro": (EntradaPerfilFinanceiro, DadosPerfilFinanceiro),
    "capacidade_poupanca": (EntradaCapacidadePoupanca, DadosCapacidadePoupanca),
    "oportunidades_corte": (EntradaOportunidadesCorte, DadosOportunidadesCorte),
    "dividas_e_parcelas": (EntradaDividasParcelas, DadosDividasParcelas),
    "simular_objetivo": (EntradaSimularObjetivo, DadosSimularObjetivo),
    "comparar_cenarios": (EntradaCompararCenarios, DadosCompararCenarios),
    "buscar_contexto_financeiro": (EntradaBuscarContexto, DadosBuscarContexto),
    "resumo_mes": (EntradaResumoMes, DadosResumoMes),
    "referencia_coorte": (EntradaReferenciaCoorte, DadosReferenciaCoorte),
}

# O mock do ciclo 000 registra as 7 ferramentas P0 e `resumo_mes`; `referencia_coorte` (P1) fica
# de fora.
FERRAMENTAS_MOCK = tuple(nome for nome in FERRAMENTAS if nome != "referencia_coorte")
