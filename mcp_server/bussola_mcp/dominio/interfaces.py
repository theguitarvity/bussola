"""Interfaces de domínio do MCP server (docs/ciclos/contratos.md §4).

`RepositorioFinanceiro` e `BuscadorContexto` são os Protocols que os ciclos consomem: o 000
entrega os fakes (`fakes.py`), o 001 entrega `RepositorioBigQuery` e o 002 entrega os buscadores
reais. Todas as consultas recebem `ate_anomes` (inclusivo): o servidor nunca enxerga o futuro
(replay temporal).
"""

from typing import Protocol, runtime_checkable

from bussola_mcp.contratos import (
    Categoria,
    EntradaCategoria,
    GastoCategoria,
    Parcela,
    PerfilMes,
    Recorrente,
    RefCoorte,
    Trecho,
)


@runtime_checkable
class RepositorioFinanceiro(Protocol):
    def usuario_existe(self, id_usuario: str) -> bool: ...

    def perfil_mensal(self, id_usuario: str, ate_anomes: int) -> list[PerfilMes]: ...

    def gastos_categoria(
        self, id_usuario: str, ate_anomes: int, desde_anomes: int | None = None
    ) -> list[GastoCategoria]: ...

    def entradas_categoria(self, id_usuario: str, ate_anomes: int) -> list[EntradaCategoria]: ...

    def recorrentes(self, id_usuario: str, ate_anomes: int) -> list[Recorrente]: ...

    def parcelas(self, id_usuario: str, ate_anomes: int) -> list[Parcela]: ...

    def categorias(self) -> list[Categoria]: ...

    def referencia_coorte(self, faixa_renda: str, macro: str | None = None) -> list[RefCoorte]: ...


@runtime_checkable
class BuscadorContexto(Protocol):
    def buscar(self, id_usuario: str, pergunta: str, k: int, ate_anomes: int) -> list[Trecho]: ...
