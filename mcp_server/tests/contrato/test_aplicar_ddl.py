"""aplicar_ddl.py (FR-021, AC11): DDL idempotente dos 4 datasets; `--dry-run` não conecta."""

import re

import pytest

from ._scripts import carregar

ad = carregar("data/scripts/aplicar_ddl.py")


def test_dry_run_imprime_os_4_create_schema_e_todas_as_tabelas(capsys):
    assert ad.main(["--dry-run", "--projeto", "meu-projeto"]) == 0
    saida = capsys.readouterr().out
    schemas = re.findall(r"CREATE SCHEMA IF NOT EXISTS `meu-projeto\.(\w+)`", saida)
    assert schemas == ["bussola_dados", "bussola_rag", "bussola_app", "bussola_app_dev"]
    tabelas = re.findall(r"CREATE TABLE IF NOT EXISTS `meu-projeto\.(\w+)\.(\w+)`", saida)
    assert len(tabelas) == 7 + 1 + 4 + 4  # dados + rag + app + app_dev
    assert ("bussola_app_dev", "planos") in tabelas
    assert ("bussola_app", "planos") in tabelas


def test_todas_as_instrucoes_sao_idempotentes_e_sem_placeholder():
    instrucoes = ad.instrucoes("meu-projeto")
    assert len(instrucoes) == 4 + 16
    for sql in instrucoes:
        assert "IF NOT EXISTS" in sql
        assert "{project}" not in sql
        assert "{dataset}" not in sql
        assert ";" not in sql


def test_aplicar_executa_cada_instrucao_uma_vez_no_cliente_injetado():
    chamadas = []

    class Job:
        def result(self):
            return []

    class Cliente:
        def query(self, sql):
            chamadas.append(sql)
            return Job()

    ad.aplicar(Cliente(), "meu-projeto")
    assert chamadas == ad.instrucoes("meu-projeto")


def test_dry_run_nao_cria_cliente_bigquery(monkeypatch):
    def proibido(*_a, **_k):
        raise AssertionError("o dry-run não pode abrir conexão")

    monkeypatch.setattr(ad, "_cliente", proibido)
    assert ad.main(["--dry-run"]) == 0


def test_projeto_padrao_vem_do_ambiente(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "projeto-do-ambiente")
    ad.main(["--dry-run"])
    assert "projeto-do-ambiente" in capsys.readouterr().out
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT")
    ad.main(["--dry-run"])
    assert "batalha-time-07-lkbv" in capsys.readouterr().out


@pytest.mark.parametrize("ruim", ["x'; DROP TABLE t; --", "Projeto Com Espaço", "", "a"])
def test_projeto_invalido_e_recusado_antes_de_entrar_no_sql(ruim):
    with pytest.raises(SystemExit):
        ad.instrucoes(ruim)
