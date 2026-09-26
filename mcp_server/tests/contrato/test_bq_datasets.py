"""Testes que dependem do GCP/base real (`make test-bq`); pulam sem credenciais ou sem base real.

- `test_os_4_datasets_existem`: valida o resultado de `data/scripts/aplicar_ddl.py` (AC11).
- `test_valores_de_referencia_do_ancora`: SC-006 (contratos §8, tolerância de 1%). Só roda com
  fixtures geradas da base real (`make fixtures`); com as fixtures sintéticas de teste, pula.
"""

import json
import os
import statistics
from pathlib import Path

import pytest

pytestmark = pytest.mark.bq

RAIZ = Path(__file__).resolve().parents[3]
FIXTURES = RAIZ / "contracts" / "fixtures"
ANCORA = "36a21505-d6d4-42d3-b319-d51a133c7269"
DATASETS = {"bussola_dados", "bussola_rag", "bussola_app", "bussola_app_dev"}


def test_os_4_datasets_existem():
    bigquery = pytest.importorskip("google.cloud.bigquery")
    projeto = os.environ.get("GOOGLE_CLOUD_PROJECT", "batalha-time-07-lkbv")
    try:
        cliente = bigquery.Client(project=projeto)
        existentes = {d.dataset_id for d in cliente.list_datasets()}
    except Exception as erro:  # sem ADC, sem rede ou sem permissão: não é falha do código
        pytest.skip(f"sem acesso ao BigQuery: {type(erro).__name__}")
    assert DATASETS <= existentes


def _perto(valor: float, referencia: float) -> bool:
    return abs(valor - referencia) <= abs(referencia) * 0.01


def _media_mensal(linhas: list[dict], trecho: str) -> float:
    total = sum(x["total"] for x in linhas if trecho in f"{x['macro']} {x['micro']}".lower())
    return total / 12


def test_valores_de_referencia_do_ancora():
    usuarios = json.loads((FIXTURES / "usuarios.json").read_text(encoding="utf-8"))
    if {u["origem"] for u in usuarios} != {"base_real"}:
        pytest.skip("fixtures sintéticas de teste; rode `make fixtures` com credenciais GCP")
    perfil = [
        p
        for p in json.loads((FIXTURES / "bussola_dados" / "perfil_mensal.json").read_text("utf-8"))
        if p["id_usuario"] == ANCORA
    ]
    gastos = [
        g
        for g in json.loads(
            (FIXTURES / "bussola_dados" / "gastos_categoria.json").read_text("utf-8")
        )
        if g["id_usuario"] == ANCORA
    ]
    referencia = {  # contratos §8, média de 2025 (ate_anomes = 202512)
        "renda": (statistics.mean(p["renda"] for p in perfil), 7451),
        "gasto": (statistics.mean(p["gasto"] for p in perfil), 4615),
        "sobra": (statistics.mean(p["sobra"] for p in perfil), 2836),
        "juros": (statistics.mean(p["juros"] for p in perfil), 61),
        "saldo_minimo": (min(p["saldo_minimo"] for p in perfil), -2072),
        "saldo_maximo": (max(p["saldo_maximo"] for p in perfil), 49321),
        "aluguel": (_media_mensal(gastos, "alug"), 1077),
        "comer_fora": (_media_mensal(gastos, "restaurante"), 364),
        "assinaturas": (_media_mensal(gastos, "assin"), 101),
    }
    fora = {k: (round(v, 2), ref) for k, (v, ref) in referencia.items() if not _perto(v, ref)}
    assert not fora, (
        f"fora de 1% do contratos §8: {fora}. Se for aluguel/comer fora/assinaturas ou juros, "
        "ajuste as regras provisórias de data/scripts/gerar_fixtures.py (questoes Q-006)."
    )
