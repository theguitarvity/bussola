"""Carrega os scripts de `data/scripts/` e `deploy/` (que não são pacotes) para testá-los."""

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def carregar(relativo: str):
    """Importa `relativo` (ex.: "data/scripts/gerar_fixtures.py") como módulo."""
    caminho = RAIZ / relativo
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo
