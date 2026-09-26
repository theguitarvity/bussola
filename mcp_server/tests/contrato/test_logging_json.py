"""Logger JSON (contratos §9): uma linha por evento, só campos permitidos, nunca prompt/segredos."""

import json
import logging

from bussola_mcp import logging_json as lj


def _linhas(capsys):
    return [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.strip()]


def test_uma_linha_json_por_evento_com_campos_do_cloud_logging(capsys):
    lj.configurar("bussola-mcp")
    lj.log_evento(
        "ferramenta_chamada",
        ferramenta="perfil_financeiro",
        ate_anomes=202506,
        latencia_ms=12,
        erro_codigo=None,
    )
    (linha,) = _linhas(capsys)
    assert linha["severity"] == "INFO"
    assert linha["message"] == "ferramenta_chamada"
    assert linha["servico"] == "bussola-mcp"
    assert linha["evento"] == "ferramenta_chamada"
    assert linha["ferramenta"] == "perfil_financeiro"
    assert linha["ate_anomes"] == 202506
    assert linha["latencia_ms"] == 12
    assert "erro_codigo" not in linha  # None não é emitido


def test_campos_fora_da_lista_sao_descartados(capsys):
    lj.configurar("bussola-mcp")
    lj.log_evento("teste", prompt="PROMPT-SECRETO", texto="lancamento", token="ya29.xyz", chave="k")
    saida = capsys.readouterr().out
    for proibido in ("PROMPT-SECRETO", "lancamento", "ya29.xyz", "prompt", "token"):
        assert proibido not in saida


def test_nivel_vem_de_log_level(capsys, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    lj.configurar("bussola-mcp")
    lj.log_evento("info_nao_sai")
    lj.log_evento("aviso_sai", nivel=logging.WARNING)
    assert [x["evento"] for x in _linhas(capsys)] == ["aviso_sai"]
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    lj.configurar("bussola-mcp")
