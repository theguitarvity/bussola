"""Gera `contracts/fixtures/` para o usuário-âncora e o de controle (contratos §8; FR-016/017).

Uso (a partir da raiz; `make fixtures` já define o PYTHONPATH):

    make fixtures                    # base real (exige gcloud/ADC); origem "base_real"
    make fixtures ARGS=--sintetico   # extrato sintético mínimo e determinístico, sem BigQuery

Como funciona (research R9/R10): a busca traz só as linhas brutas dos 2 usuários por consulta
parametrizada e somente leitura; `agregar_extrato` é a ÚNICA implementação da agregação (a mesma
para dados reais e sintéticos). Os goldens são PROVISÓRIOS: cálculo de referência simples, dentro
deste script, que o ciclo 001 substitui (PR `contracts:`). Toda saída é validada pelos modelos de
`bussola_mcp.contratos` antes de ser gravada. Regras provisórias (questoes Q-006): juros,
recorrentes e categorias; o dono real é o 001.
"""

import argparse
import json
import math
import os
import re
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from bussola_mcp import contratos as c

RAIZ = Path(__file__).resolve().parents[2]
ANCORA = "36a21505-d6d4-42d3-b319-d51a133c7269"
CONTROLE = "31e94f2f-1463-49f9-a41a-b3f220ed976a"
MESES = list(range(202501, 202513))
CORTES = (202506, 202512)

# Entradas fixas usadas para gerar cada golden (documentadas em ferramentas/_entradas.json).
ENTRADAS_GOLDEN = {
    "oportunidades_corte": {"top_n": 5},
    "simular_objetivo": {"valor_alvo": 60000.0, "prazo_meses": 36},
    "comparar_cenarios": {"valor_alvo": 60000.0, "prazo_meses": 36},
    "buscar_contexto_financeiro": {"pergunta": "quanto gasto com comer fora?", "k": 5},
}
PCT_CAPACIDADE = {"conservador": 0.40, "equilibrado": 0.60, "acelerado": 0.80}  # contratos §4
PALAVRAS_DISCRICIONARIAS = ("restaurante", "assinatura", "lazer", "delivery", "compras")
CORTE_MAX_PCT = 0.30  # provisório (Q-006)
MIN_MESES_RECORRENTE = 3  # provisório (Q-006)

# Consulta parametrizada e somente leitura; os UUIDs entram só por @ids, nunca no texto do SQL.
SQL_EXTRATO = """
SELECT id_usuario, anomesdia, anomes, tipo, descr, vlr, nom_cate_macro, nom_cate_micro,
       saldo_apos, parcela_atual, parcela_total
FROM hackathon_dados.extrato_sintetico
WHERE id_usuario IN UNNEST(@ids)
ORDER BY id_usuario, anomesdia
"""

AVISO_REGRAS = (
    "AVISO: regras provisórias (questoes Q-006) — juros = saídas com 'juros' na microcategoria; "
    f"recorrente = descrição em >= {MIN_MESES_RECORRENTE} meses; discricionária por palavra-chave. "
    "Os nomes reais das categorias são desconhecidos: confira os valores de referência do âncora "
    "(contratos §8, tolerância de 1%) e ajuste as regras."
)


# --- extrato: busca real e sintético ------------------------------------------------------------


def buscar_linhas(cliente, ids: list[str]) -> list[dict]:
    """Linhas brutas do extrato para `ids`. `cliente` é um `bigquery.Client` (injetável)."""
    from google.cloud import bigquery

    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", ids)]
    )
    return [dict(linha) for linha in cliente.query(SQL_EXTRATO, job_config=config).result()]


def extrato_sintetico() -> list[dict]:
    """Extrato mínimo e determinístico (2 usuários x 12 meses), só para teste. Sem números reais."""
    perfis = {
        ANCORA: {"salario": 7000.0, "aluguel": 1100.0, "saldo0": 500.0, "restaurante": 300.0},
        CONTROLE: {"salario": 6500.0, "aluguel": 1650.0, "saldo0": 1500.0, "restaurante": 600.0},
    }
    linhas = []
    for id_usuario, p in perfis.items():
        saldo = p["saldo0"]
        for anomes in MESES:
            mes = anomes % 100
            lancamentos = [  # (dia, tipo, descr, vlr, macro, micro, parcela_atual, parcela_total)
                (
                    3,
                    "S",
                    "cart debito mercado",
                    700.0 + 25.0 * (mes % 4),
                    "Mercado",
                    "Supermercado",
                ),
                (
                    5,
                    "E",
                    "credito salario empresa",
                    p["salario"],
                    "Salários e bonificações",
                    "Salário",
                ),
                (
                    7,
                    "E",
                    "pix recebido autonomo",
                    400.0 + 50.0 * (mes % 3),
                    "Recebimentos diversos",
                    "Pix",
                ),
                (10, "S", "pix transf alug", p["aluguel"], "Casa", "Aluguel"),
                (
                    12,
                    "S",
                    "cart credito restaurante centro",
                    p["restaurante"] + 40.0 * (mes % 4),
                    "Alimentação",
                    "Restaurantes",
                ),
                (15, "S", "assin streaming video", 39.9, "Lazer", "Assinaturas"),
                (16, "S", "assin musica", 21.9, "Lazer", "Assinaturas"),
                (
                    20,
                    "S",
                    "cart credito corrida app",
                    120.0 + 30.0 * (mes % 3),
                    "Transporte",
                    "Aplicativo",
                ),
            ]
            lancamentos = [(*lc, None, None) for lc in lancamentos]
            if mes % 3 == 0:
                lancamentos.append(
                    (
                        25,
                        "S",
                        "juros cheque especial",
                        58.4,
                        "Produtos financeiros",
                        "Juros",
                        None,
                        None,
                    )
                )
            if 3 <= mes <= 8:
                k = mes - 2
                lancamentos.append(
                    (
                        18,
                        "S",
                        f"cart credito loja esport parc {k}/6",
                        180.0,
                        "Compras",
                        "Loja de esportes",
                        k,
                        6,
                    )
                )
            for dia, tipo, descr, vlr, macro, micro, pa, pt in sorted(
                lancamentos, key=lambda lc: (lc[0], lc[2])
            ):
                saldo = round(saldo + (vlr if tipo == "E" else -vlr), 2)
                linhas.append(
                    {
                        "id_usuario": id_usuario,
                        "anomesdia": f"{anomes // 100}-{mes:02d}-{dia:02d}T00:00:00",
                        "anomes": anomes,
                        "tipo": tipo,
                        "descr": descr,
                        "vlr": vlr,
                        "nom_cate_macro": macro,
                        "nom_cate_micro": micro,
                        "saldo_apos": saldo,
                        "parcela_atual": pa,
                        "parcela_total": pt,
                    }
                )
    return linhas


# --- agregação única (equivale ao que o 001 fará em SQL) ----------------------------------------


def _r(x: float) -> float:
    return round(x, 2)


def _norm_descr(descr: str) -> str:
    sem_parcela = re.sub(r"parc\s*\d+/\d+", "", descr.lower())
    return re.sub(r"\s+", " ", re.sub(r"\d+", "", sem_parcela)).strip()


def agregar_extrato(linhas: list[dict]) -> dict[str, list[dict]]:
    """Linhas brutas -> tabelas de `bussola_dados` (contratos §3) para os usuários presentes."""
    linhas = sorted(linhas, key=lambda x: (x["id_usuario"], x["anomes"], str(x["anomesdia"])))
    por_mes = defaultdict(list)
    for linha in linhas:
        por_mes[(linha["id_usuario"], linha["anomes"])].append(linha)

    perfil, gastos, entradas, parcelas = [], [], [], []
    for (usuario, anomes), rows in sorted(por_mes.items()):
        renda = sum(x["vlr"] for x in rows if x["tipo"] == "E")
        gasto = sum(x["vlr"] for x in rows if x["tipo"] == "S")
        primeiro = rows[0]
        inicial = primeiro["saldo_apos"] - (
            primeiro["vlr"] if primeiro["tipo"] == "E" else -primeiro["vlr"]
        )
        saldos = [x["saldo_apos"] for x in rows]
        juros = sum(
            x["vlr"]
            for x in rows
            if x["tipo"] == "S" and "juros" in (x["nom_cate_micro"] or "").lower()
        )
        perfil.append(
            {
                "id_usuario": usuario,
                "anomes": anomes,
                "renda": _r(renda),
                "gasto": _r(gasto),
                "sobra": _r(renda - gasto),
                "saldo_inicial": _r(inicial),
                "saldo_final": _r(saldos[-1]),
                "saldo_minimo": _r(min(saldos)),
                "saldo_maximo": _r(max(saldos)),
                "juros": _r(juros),
            }
        )
        for tipo, destino in (("S", gastos), ("E", entradas)):
            grupos = defaultdict(list)
            for x in rows:
                if x["tipo"] == tipo:
                    grupos[(x["nom_cate_macro"], x["nom_cate_micro"])].append(x["vlr"])
            for (macro, micro), valores in sorted(grupos.items()):
                destino.append(
                    {
                        "id_usuario": usuario,
                        "anomes": anomes,
                        "macro": macro,
                        "micro": micro,
                        "total": _r(sum(valores)),
                        "qtd": len(valores),
                    }
                )
        for x in rows:
            if x["parcela_total"] is not None:
                parcelas.append(
                    {
                        "id_usuario": usuario,
                        "anomes": anomes,
                        "descr": x["descr"],
                        "macro": x["nom_cate_macro"],
                        "parcela_atual": int(x["parcela_atual"]),
                        "parcela_total": int(x["parcela_total"]),
                        "vlr": _r(x["vlr"]),
                    }
                )

    return {
        "perfil_mensal": perfil,
        "gastos_categoria": gastos,
        "entradas_categoria": entradas,
        "recorrentes": _recorrentes(por_mes),
        "parcelas": parcelas,
        "categorias": _categorias(linhas),
        "referencia_coorte": [],  # exige a população inteira, que o gerador não lê (Q-007)
    }


def _recorrentes(por_mes) -> list[dict]:
    ocorrencias = defaultdict(
        lambda: defaultdict(float)
    )  # (usuario, descr_norm, macro, micro) -> mes -> valor
    for (usuario, anomes), rows in por_mes.items():
        for x in rows:
            if x["tipo"] == "S" and x["parcela_total"] is None:
                chave = (usuario, _norm_descr(x["descr"]), x["nom_cate_macro"], x["nom_cate_micro"])
                ocorrencias[chave][anomes] += x["vlr"]
    saida = []
    for (usuario, descr_norm, macro, micro), meses in sorted(ocorrencias.items()):
        if len(meses) >= MIN_MESES_RECORRENTE:
            for anomes, valor in sorted(meses.items()):
                saida.append(
                    {
                        "id_usuario": usuario,
                        "anomes": anomes,
                        "descr_norm": descr_norm,
                        "macro": macro,
                        "micro": micro,
                        "valor": _r(valor),
                    }
                )
    return saida


def _categorias(linhas: list[dict]) -> list[dict]:
    pares = sorted({(x["nom_cate_macro"], x["nom_cate_micro"]) for x in linhas if x["tipo"] == "S"})
    saida = []
    for macro, micro in pares:
        discricionaria = any(p in f"{macro} {micro}".lower() for p in PALAVRAS_DISCRICIONARIAS)
        saida.append(
            {
                "macro": macro,
                "micro": micro,
                "discricionaria": discricionaria,
                "corte_max_pct": CORTE_MAX_PCT if discricionaria else 0.0,
            }
        )
    return saida


# --- goldens de referência (provisórios; o 001 substitui) ---------------------------------------


def _fonte(ferramenta: str, tabelas: list[str], fim: int, inicio: int = 202501) -> dict:
    return {
        "ferramenta": ferramenta,
        "tabelas": [f"bussola_dados.{t}" for t in tabelas],
        "periodo": {"inicio": inicio, "fim": fim},
    }


def _do_usuario(linhas: list[dict], usuario: str, ate: int) -> list[dict]:
    return [x for x in linhas if x["id_usuario"] == usuario and x["anomes"] <= ate]


def _capacidade(perfil: list[dict]) -> dict:
    sobras = [p["sobra"] for p in perfil]
    return {
        "sobra_media": _r(statistics.mean(sobras)),
        "sobra_mediana": _r(statistics.median(sobras)),
        "desvio_padrao": _r(statistics.pstdev(sobras)),
        "meses_negativos": sum(s < 0 for s in sobras),
        "meses_considerados": len(sobras),
    }


def _cortes(t: dict, usuario: str, ate: int, n_meses: int, top_n: int) -> list[dict]:
    pct = {
        (k["macro"], k["micro"]): k["corte_max_pct"] for k in t["categorias"] if k["discricionaria"]
    }
    totais = defaultdict(float)
    for g in _do_usuario(t["gastos_categoria"], usuario, ate):
        if (g["macro"], g["micro"]) in pct:
            totais[(g["macro"], g["micro"])] += g["total"]
    itens = []
    for (macro, micro), total in totais.items():
        media = total / n_meses
        itens.append(
            {
                "macro": macro,
                "micro": micro,
                "media_mensal": _r(media),
                "discricionaria": True,
                "economia_potencial_mensal": _r(media * pct[(macro, micro)]),
                "criterio": f"discricionária; corte máximo de {pct[(macro, micro)]:.0%} da média",
            }
        )
    itens.sort(key=lambda i: (-i["economia_potencial_mensal"], i["macro"], i["micro"]))
    return itens[:top_n]


def gerar_golden(t: dict, usuario: str, ferramenta: str, ate: int) -> dict:
    """Envelope esperado (Resposta) da `ferramenta` para `usuario` com corte `ate`."""
    perfil = _do_usuario(t["perfil_mensal"], usuario, ate)
    n = len(perfil)
    cap = _capacidade(perfil)
    avisos: list[str] = []
    if ferramenta == "perfil_financeiro":
        rendas = defaultdict(float)
        for e in _do_usuario(t["entradas_categoria"], usuario, ate):
            rendas[(e["macro"], e["micro"])] += e["total"]
        fontes = sorted(
            ({"macro": m, "micro": mi, "media": _r(v / n)} for (m, mi), v in rendas.items()),
            key=lambda f: (-f["media"], f["macro"], f["micro"]),
        )
        dados = {
            "renda_media": _r(statistics.mean(p["renda"] for p in perfil)),
            "gasto_medio": _r(statistics.mean(p["gasto"] for p in perfil)),
            "sobra_media": cap["sobra_media"],
            "sobra_mediana": cap["sobra_mediana"],
            "fontes_renda": fontes,
            "saldo": {
                "minimo": min(p["saldo_minimo"] for p in perfil),
                "maximo": max(p["saldo_maximo"] for p in perfil),
                "atual": perfil[-1]["saldo_final"],
            },
            "serie_mensal": [
                {
                    "anomes": p["anomes"],
                    "renda": p["renda"],
                    "gasto": p["gasto"],
                    "sobra": p["sobra"],
                }
                for p in perfil
            ],
            "meses_considerados": n,
        }
        negativos = sum(p["saldo_minimo"] < 0 for p in perfil)
        if negativos:
            avisos.append(
                f"Saldo ficou negativo em {negativos} "
                f"{'mês' if negativos == 1 else 'meses'} do período."
            )
        tabelas = ["perfil_mensal", "entradas_categoria"]
    elif ferramenta == "capacidade_poupanca":
        dados, tabelas = cap, ["perfil_mensal"]
    elif ferramenta == "oportunidades_corte":
        top_n = ENTRADAS_GOLDEN["oportunidades_corte"]["top_n"]
        dados = {"categorias": _cortes(t, usuario, ate, n, top_n)}
        tabelas = ["gastos_categoria", "categorias"]
    elif ferramenta == "dividas_e_parcelas":
        ativas = [
            p
            for p in _do_usuario(t["parcelas"], usuario, ate)
            if p["anomes"] == ate and p["parcela_atual"] < p["parcela_total"]
        ]
        renda_media = statistics.mean(p["renda"] for p in perfil)
        valor_total = sum(p["vlr"] for p in ativas)
        dados = {
            "parcelas_ativas": [
                {
                    "descr": p["descr"],
                    "parcela_atual": p["parcela_atual"],
                    "parcela_total": p["parcela_total"],
                    "valor": p["vlr"],
                    "meses_restantes": p["parcela_total"] - p["parcela_atual"],
                }
                for p in ativas
            ],
            "juros_pagos_media": _r(statistics.mean(p["juros"] for p in perfil)),
            "comprometimento_renda_pct": _r(valor_total / renda_media * 100),
        }
        tabelas = ["parcelas", "perfil_mensal"]
    elif ferramenta == "simular_objetivo":
        entrada = ENTRADAS_GOLDEN["simular_objetivo"]
        aporte = _r(entrada["valor_alvo"] / entrada["prazo_meses"])
        dados = {
            "modo": "prazo",  # a entrada foi o prazo; o aporte foi calculado (questoes Q-011)
            "valor_alvo": entrada["valor_alvo"],
            "aporte_mensal": aporte,
            "prazo_meses": entrada["prazo_meses"],
            "viavel": aporte <= cap["sobra_mediana"],
            "folga_mensal": _r(cap["sobra_mediana"] - aporte),
            "premissas": {
                "rendimento_mensal": 0.0,
                "saldo_inicial": 0.0,
                "base_capacidade": "sobra_mediana",
                "sobra_mediana": cap["sobra_mediana"],
            },
        }
        tabelas = ["perfil_mensal"]
    elif ferramenta == "comparar_cenarios":
        entrada = ENTRADAS_GOLDEN["comparar_cenarios"]
        cortes = [
            {
                "macro": k["macro"],
                "micro": k["micro"],
                "valor_mensal": k["economia_potencial_mensal"],
            }
            for k in _cortes(t, usuario, ate, n, 3)
        ]
        cenarios = []
        for nome, pct in PCT_CAPACIDADE.items():
            sugeridos = cortes if nome == "acelerado" else []
            base = _r(pct * cap["sobra_mediana"]) if cap["sobra_mediana"] > 0 else 0.0
            aporte = _r(base + sum(k["valor_mensal"] for k in sugeridos))
            prazo = math.ceil(entrada["valor_alvo"] / aporte) if aporte > 0 else 0
            viavel = 0 < prazo <= entrada["prazo_meses"]
            trade = [
                f"Aporte de R$ {aporte:.0f}/mês; atinge o valor-alvo em {prazo} meses."
                if prazo
                else "Sem capacidade de poupança no período."
            ]
            trade.append(
                f"Cabe no prazo desejado de {entrada['prazo_meses']} meses."
                if viavel
                else f"Passa do prazo desejado de {entrada['prazo_meses']} meses."
            )
            trade += [
                f"Exige reduzir R$ {k['valor_mensal']:.0f}/mês em {k['micro']}." for k in sugeridos
            ]
            cenarios.append(
                {
                    "nome": nome,
                    "pct_capacidade": pct,
                    "aporte_mensal": aporte,
                    "prazo_meses": prazo,
                    "viavel": viavel,
                    "cortes_sugeridos": sugeridos,
                    "trade_offs": trade,
                }
            )
        dados = {
            "cenarios": cenarios,
            "regras": {
                "pct_capacidade": PCT_CAPACIDADE,
                "base": "sobra_mediana",
                "rendimento_mensal": 0.0,
                "saldo_inicial": 0.0,
                "acelerado_inclui_cortes": True,
            },
        }
        tabelas = ["perfil_mensal", "gastos_categoria", "categorias"]
    else:
        raise ValueError(f"ferramenta sem golden: {ferramenta}")
    return {"dados": dados, "fonte": _fonte(ferramenta, tabelas, ate), "avisos": avisos}


def gerar_resumo_mes(t: dict, usuario: str, anomes: int) -> dict:
    perfil = next(
        p for p in t["perfil_mensal"] if p["id_usuario"] == usuario and p["anomes"] == anomes
    )
    macros = defaultdict(float)
    for g in t["gastos_categoria"]:
        if g["id_usuario"] == usuario and g["anomes"] == anomes:
            macros[g["macro"]] += g["total"]
    dados = {
        "anomes": anomes,
        "renda": perfil["renda"],
        "gasto": perfil["gasto"],
        "sobra": perfil["sobra"],
        "gastos_macro": [
            {"macro": m, "total": _r(v)}
            for m, v in sorted(macros.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    }
    fonte = _fonte("resumo_mes", ["perfil_mensal", "gastos_categoria"], anomes, inicio=anomes)
    return {"dados": dados, "fonte": fonte, "avisos": []}


def gerar_trechos(t: dict) -> list[dict]:
    """Trechos determinísticos no formato de `buscar_contexto_financeiro`."""

    def ficha(usuario: str, anomes: int) -> dict:
        perfil = next(
            p for p in t["perfil_mensal"] if p["id_usuario"] == usuario and p["anomes"] == anomes
        )
        gastos = sorted(
            (
                g
                for g in t["gastos_categoria"]
                if g["id_usuario"] == usuario and g["anomes"] == anomes
            ),
            key=lambda g: (-g["total"], g["macro"]),
        )[:2]
        maiores = ", ".join(f"{g['macro']} (R$ {g['total']:.2f})" for g in gastos)
        texto = (
            f"Ficha de {anomes // 100}-{anomes % 100:02d}: renda R$ {perfil['renda']:.2f}, gasto "
            f"R$ {perfil['gasto']:.2f}, sobra R$ {perfil['sobra']:.2f}. Maiores gastos: {maiores}."
        )
        return {
            "doc_id": f"ficha_mensal:{usuario}:{anomes}",
            "tipo": "ficha_mensal",
            "anomes": anomes,
            "texto": texto,
            "score": 0.0,
            "origem": {"id_usuario": usuario, "anomes": anomes, "categoria": None},
        }

    def anual(usuario: str) -> dict:
        perfil = [p for p in t["perfil_mensal"] if p["id_usuario"] == usuario]
        renda = statistics.mean(p["renda"] for p in perfil)
        gasto = statistics.mean(p["gasto"] for p in perfil)
        sobra = statistics.median(p["sobra"] for p in perfil)
        texto = (
            f"Perfil de 2025: renda média R$ {renda:.2f}, gasto médio R$ {gasto:.2f}, "
            f"sobra mediana R$ {sobra:.2f}."
        )
        return {
            "doc_id": f"perfil_anual:{usuario}:202512",
            "tipo": "perfil_anual",
            "anomes": 202512,
            "texto": texto,
            "score": 0.0,
            "origem": {"id_usuario": usuario, "anomes": 202512, "categoria": None},
        }

    totais = defaultdict(float)
    for g in t["gastos_categoria"]:
        totais[g["macro"]] += g["total"]
    macro = sorted(totais, key=lambda m: (-totais[m], m))[0]
    usuarios = {p["id_usuario"] for p in t["perfil_mensal"]}
    media = totais[macro] / (12 * len(usuarios))
    coorte = {
        "doc_id": f"coorte:{macro}",
        "tipo": "coorte",
        "anomes": None,
        "texto": (
            f"Referência de coorte (exemplo de teste com {len(usuarios)} usuários): "
            f"a média mensal de gasto em {macro} é R$ {media:.2f}."
        ),
        "score": 0.0,
        "origem": {"id_usuario": None, "anomes": None, "categoria": macro},
    }
    return [ficha(ANCORA, 202503), anual(ANCORA), ficha(CONTROLE, 202503), coorte]


# --- gravação ----------------------------------------------------------------------------------


def _escrever(caminho: Path, obj) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gerar(destino: Path, linhas: list[dict], origem: str) -> None:
    """Agrega `linhas`, valida tudo pelos modelos e grava `destino` (recria as subpastas)."""
    destino = Path(destino)
    tabelas = agregar_extrato(linhas)
    modelos = {
        "perfil_mensal": c.PerfilMes,
        "gastos_categoria": c.GastoCategoria,
        "entradas_categoria": c.EntradaCategoria,
        "recorrentes": c.Recorrente,
        "parcelas": c.Parcela,
        "categorias": c.Categoria,
        "referencia_coorte": c.RefCoorte,
    }
    for nome, modelo in modelos.items():
        for linha in tabelas[nome]:
            modelo.model_validate(linha)
    presentes = {p["id_usuario"] for p in tabelas["perfil_mensal"]}
    if presentes != {ANCORA, CONTROLE}:
        raise SystemExit(
            f"o extrato precisa conter exatamente o âncora e o controle; veio: {sorted(presentes)}"
        )

    for sub in ("bussola_dados", "ferramentas", "rag"):
        shutil.rmtree(destino / sub, ignore_errors=True)
    usuarios = [
        {"id_usuario": ANCORA, "papel": "ancora", "origem": origem},
        {"id_usuario": CONTROLE, "papel": "controle", "origem": origem},
    ]
    for u in usuarios:
        c.UsuarioFixture.model_validate(u)
    _escrever(destino / "usuarios.json", usuarios)
    for nome, rows in tabelas.items():
        _escrever(destino / "bussola_dados" / f"{nome}.json", rows)

    def validar_e_escrever(caminho: Path, ferramenta: str, envelope: dict) -> None:
        c.Resposta.model_validate(envelope)
        c.FERRAMENTAS[ferramenta][1].model_validate(envelope["dados"])
        _escrever(caminho, envelope)

    _escrever(destino / "ferramentas" / "_entradas.json", ENTRADAS_GOLDEN)
    for ferramenta in (
        "perfil_financeiro",
        "capacidade_poupanca",
        "oportunidades_corte",
        "dividas_e_parcelas",
        "simular_objetivo",
        "comparar_cenarios",
    ):
        for corte in CORTES:
            validar_e_escrever(
                destino / "ferramentas" / f"{ferramenta}__ate_{corte}.json",
                ferramenta,
                gerar_golden(tabelas, ANCORA, ferramenta, corte),
            )
    for anomes in MESES:
        validar_e_escrever(
            destino / "ferramentas" / f"resumo_mes__{anomes}.json",
            "resumo_mes",
            gerar_resumo_mes(tabelas, ANCORA, anomes),
        )
    trechos = gerar_trechos(tabelas)
    for trecho in trechos:
        c.Trecho.model_validate(trecho)
    _escrever(destino / "rag" / "trechos_exemplo.json", trechos)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sintetico", action="store_true", help="usa o extrato sintético de teste")
    ap.add_argument("--destino", type=Path, default=RAIZ / "contracts" / "fixtures")
    ap.add_argument(
        "--projeto", default=os.environ.get("GOOGLE_CLOUD_PROJECT", "batalha-time-07-lkbv")
    )
    args = ap.parse_args(argv)
    if args.sintetico:
        gerar(args.destino, extrato_sintetico(), origem="sintetico_teste")
    else:
        from google.cloud import bigquery

        print(AVISO_REGRAS, file=sys.stderr)
        linhas = buscar_linhas(bigquery.Client(project=args.projeto), [ANCORA, CONTROLE])
        gerar(args.destino, linhas, origem="base_real")
    print(f"fixtures gravadas em {args.destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
