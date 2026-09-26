"""Fakes de `RepositorioFinanceiro` e `BuscadorContexto` sobre `contracts/fixtures/` (§4/§8).

Servem aos ciclos consumidores e ao mock do MCP enquanto não há BigQuery. O diretório das
fixtures vem de `BUSSOLA_FIXTURES_DIR` (a imagem Docker o define); por padrão, usa
`contracts/fixtures/` do repositório. O buscador é ingênuo de propósito (palavras em comum),
determinístico e só um fake.
"""

import json
import os
import re
from pathlib import Path

from bussola_mcp import contratos as c


def diretorio_fixtures() -> Path:
    padrao = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
    return Path(os.environ.get("BUSSOLA_FIXTURES_DIR") or padrao)


def _json(relativo: str):
    return json.loads((diretorio_fixtures() / relativo).read_text(encoding="utf-8"))


def usuarios() -> list[c.UsuarioFixture]:
    return [c.UsuarioFixture.model_validate(u) for u in _json("usuarios.json")]


def golden(ferramenta: str, corte: int) -> dict:
    """Envelope esperado (`Resposta`) da ferramenta para o âncora no corte 202506 ou 202512."""
    return _json(f"ferramentas/{ferramenta}__ate_{corte}.json")


def resumo_mes(anomes: int) -> dict:
    """Envelope esperado de `resumo_mes` para o âncora no mês `anomes`."""
    return _json(f"ferramentas/resumo_mes__{anomes}.json")


class RepositorioFake:
    """Implementa `RepositorioFinanceiro` lendo `bussola_dados/*.json`."""

    def __init__(self) -> None:
        def tabela(nome: str, modelo):
            return [modelo.model_validate(x) for x in _json(f"bussola_dados/{nome}.json")]

        self._usuarios = {u.id_usuario for u in usuarios()}
        self._perfil = tabela("perfil_mensal", c.PerfilMes)
        self._gastos = tabela("gastos_categoria", c.GastoCategoria)
        self._entradas = tabela("entradas_categoria", c.EntradaCategoria)
        self._recorrentes = tabela("recorrentes", c.Recorrente)
        self._parcelas = tabela("parcelas", c.Parcela)
        self._categorias = tabela("categorias", c.Categoria)
        self._coorte = tabela("referencia_coorte", c.RefCoorte)

    @staticmethod
    def _do_usuario(linhas, id_usuario: str, ate_anomes: int, desde_anomes: int | None = None):
        return [
            x
            for x in linhas
            if x.id_usuario == id_usuario
            and x.anomes <= ate_anomes
            and (desde_anomes is None or x.anomes >= desde_anomes)
        ]

    def usuario_existe(self, id_usuario: str) -> bool:
        return id_usuario in self._usuarios

    def perfil_mensal(self, id_usuario: str, ate_anomes: int) -> list[c.PerfilMes]:
        return self._do_usuario(self._perfil, id_usuario, ate_anomes)

    def gastos_categoria(
        self, id_usuario: str, ate_anomes: int, desde_anomes: int | None = None
    ) -> list[c.GastoCategoria]:
        return self._do_usuario(self._gastos, id_usuario, ate_anomes, desde_anomes)

    def entradas_categoria(self, id_usuario: str, ate_anomes: int) -> list[c.EntradaCategoria]:
        return self._do_usuario(self._entradas, id_usuario, ate_anomes)

    def recorrentes(self, id_usuario: str, ate_anomes: int) -> list[c.Recorrente]:
        return self._do_usuario(self._recorrentes, id_usuario, ate_anomes)

    def parcelas(self, id_usuario: str, ate_anomes: int) -> list[c.Parcela]:
        return self._do_usuario(self._parcelas, id_usuario, ate_anomes)

    def categorias(self) -> list[c.Categoria]:
        return list(self._categorias)

    def referencia_coorte(self, faixa_renda: str, macro: str | None = None) -> list[c.RefCoorte]:
        return [
            r
            for r in self._coorte
            if r.faixa_renda == faixa_renda and (macro is None or r.macro == macro)
        ]


def _palavras(texto: str) -> set[str]:
    return {p for p in re.findall(r"\w+", texto.lower()) if len(p) > 2}


def _pontuar(alvo: set[str], texto: str) -> float:
    return round(len(alvo & _palavras(texto)) / max(len(alvo), 1), 4)


class BuscadorFake:
    """Implementa `BuscadorContexto` sobre `rag/trechos_exemplo.json`.

    Aplica o filtro de escopo de contratos §3:
    `(id_usuario = X OR tipo = 'coorte') AND (anomes IS NULL OR anomes <= ate_anomes)`.
    """

    def __init__(self) -> None:
        self._trechos = [c.Trecho.model_validate(t) for t in _json("rag/trechos_exemplo.json")]

    def buscar(self, id_usuario: str, pergunta: str, k: int, ate_anomes: int) -> list[c.Trecho]:
        alvo = _palavras(pergunta)
        candidatos = [
            t
            for t in self._trechos
            if (t.origem.id_usuario == id_usuario or t.tipo == "coorte")
            and (t.anomes is None or t.anomes <= ate_anomes)
        ]
        pontuados = [t.model_copy(update={"score": _pontuar(alvo, t.texto)}) for t in candidatos]
        pontuados.sort(key=lambda t: (-t.score, t.doc_id))
        return pontuados[:k]
