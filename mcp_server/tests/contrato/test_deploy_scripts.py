"""Scripts de deploy (FR-023/FR-024, AC13): sintaxe, `DRY_RUN`, e confirmação humana no IAM."""

import os
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
DEPLOY = RAIZ / "deploy"
SCRIPTS = ["build_push.sh", "deploy.sh", "iam_datasets.sh"]


@pytest.fixture
def binarios_falsos(tmp_path):
    """docker/gcloud/bq/curl falsos: registram qualquer chamada e falham. Prova que nada executa."""
    log = tmp_path / "chamadas.log"
    for nome in ("docker", "gcloud", "bq", "curl"):
        exe = tmp_path / nome
        exe.write_text(f'#!/bin/sh\necho "{nome} $*" >> "{log}"\nexit 1\n', encoding="utf-8")
        exe.chmod(0o755)
    return tmp_path, log


def _rodar(script: str, *args: str, binarios, dry_run: bool = True, **env_extra):
    pasta, _log = binarios
    env = {
        "PATH": f"{pasta}:{os.environ['PATH']}",
        "HOME": os.environ.get("HOME", "/tmp"),
        **({"DRY_RUN": "1"} if dry_run else {}),
        **env_extra,
    }
    return subprocess.run(
        ["bash", str(DEPLOY / script), *args],
        cwd=RAIZ,
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # sem terminal de controle: /dev/tty indisponível
    )


@pytest.mark.parametrize("script", SCRIPTS)
def test_sintaxe_bash(script):
    subprocess.run(["bash", "-n", str(DEPLOY / script)], check=True)


def test_build_push_dry_run_imprime_o_buildx_amd64_e_nao_executa(binarios_falsos):
    r = _rodar("build_push.sh", "bussola-mcp", binarios=binarios_falsos)
    assert r.returncode == 0, r.stderr
    assert "docker buildx build --platform linux/amd64 -f mcp_server/Dockerfile" in r.stdout
    assert "us-central1-docker.pkg.dev/batalha-time-07-lkbv/agentes/bussola-mcp:" in r.stdout
    assert not binarios_falsos[1].exists()


def test_build_push_do_agente_usa_o_dockerfile_do_agente(binarios_falsos):
    r = _rodar("build_push.sh", "bussola-agent", binarios=binarios_falsos)
    assert "-f agent/Dockerfile" in r.stdout
    assert "agentes/bussola-agent:" in r.stdout


@pytest.mark.parametrize("args", [(), ("outro-servico",), ("bussola-mcp", "extra")])
def test_build_push_argumentos_invalidos_saem_com_2(args, binarios_falsos):
    assert _rodar("build_push.sh", *args, binarios=binarios_falsos).returncode == 2


def test_deploy_do_mcp_e_privado_com_tag_e_sem_trafego(binarios_falsos):
    r = _rodar("deploy.sh", "bussola-mcp", binarios=binarios_falsos)
    assert r.returncode == 0, r.stderr
    assert "gcloud run deploy bussola-mcp" in r.stdout
    assert "--region us-central1" in r.stdout
    assert "--no-allow-unauthenticated" in r.stdout
    assert re.search(r"(?<!no-)--allow-unauthenticated", r.stdout) is None
    assert "--tag c000" in r.stdout
    assert "--no-traffic" in r.stdout
    assert not binarios_falsos[1].exists()


def test_deploy_aceita_outra_tag_e_a_flag_no_traffic(binarios_falsos):
    r = _rodar(
        "deploy.sh", "bussola-mcp", "--tag", "c001", "--no-traffic", binarios=binarios_falsos
    )
    assert r.returncode == 0, r.stderr
    assert "--tag c001" in r.stdout
    assert "--no-traffic" in r.stdout


def test_deploy_do_agente_leva_oidc_max_instances_e_a_url_do_mcp(binarios_falsos):
    r = _rodar("deploy.sh", "bussola-agent", binarios=binarios_falsos, BUSSOLA_MODEL="gemini-x")
    assert r.returncode == 0, r.stderr
    assert "--max-instances=1" in r.stdout
    assert "MCP_USE_OIDC=TRUE" in r.stdout
    assert "MCP_URL=" in r.stdout
    assert "BUSSOLA_MODEL=gemini-x" in r.stdout
    assert "--no-allow-unauthenticated" in r.stdout


def test_deploy_do_agente_sem_modelo_aborta_apontando_o_smoke(binarios_falsos):
    r = _rodar("deploy.sh", "bussola-agent", binarios=binarios_falsos)
    assert r.returncode != 0
    assert "smoke_modelos" in r.stderr


@pytest.mark.parametrize("args", [(), ("nao-existe",), ("bussola-mcp", "--com-trafego")])
def test_deploy_argumentos_invalidos_saem_com_2(args, binarios_falsos):
    assert _rodar("deploy.sh", *args, binarios=binarios_falsos).returncode == 2


def test_iam_dry_run_lista_as_4_concessoes_e_nao_executa(binarios_falsos):
    r = _rodar("iam_datasets.sh", binarios=binarios_falsos)
    assert r.returncode == 0, r.stderr
    for dataset, papel in [
        ("bussola_dados", "roles/bigquery.dataViewer"),
        ("bussola_rag", "roles/bigquery.dataViewer"),
        ("bussola_app", "roles/bigquery.dataEditor"),
        ("bussola_app_dev", "roles/bigquery.dataEditor"),
    ]:
        assert re.search(rf"GRANT `{papel}` ON SCHEMA `[^`]*\.{dataset}`", r.stdout), dataset
    assert "1061873050224-compute@developer.gserviceaccount.com" in r.stdout
    assert not binarios_falsos[1].exists()


def test_iam_sem_terminal_recusa_e_nao_executa_nada(binarios_falsos):
    r = _rodar("iam_datasets.sh", binarios=binarios_falsos, dry_run=False)
    assert r.returncode != 0
    assert "terminal" in r.stderr
    assert not binarios_falsos[1].exists()


def test_iam_nao_tem_como_dispensar_a_confirmacao_humana():
    texto = (DEPLOY / "iam_datasets.sh").read_text(encoding="utf-8")
    assert "/dev/tty" in texto
    assert re.search(r"--yes|--force|--no-confirm|\s-y\b|CONFIRMO=|AUTO_?APPROVE", texto) is None
