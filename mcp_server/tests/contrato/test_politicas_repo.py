"""Políticas do repositório (constituição II e IV; AC1/AC3/SC-002/SC-008).

Cobre: artefatos do ciclo 000 existem, mapa de contratos sem `web/`, `env.example` = contratos
§7, sem segredos versionados e sem SQL montado por concatenação (também responde pelo
"test_sem_segredos" citado no plano).
"""

import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
CONTRATOS = RAIZ / "docs" / "ciclos" / "contratos.md"

ARTEFATOS_000 = [
    "CLAUDE.md",
    "Makefile",
    ".specify",
    "contracts/bigquery/bussola_dados.sql",
    "contracts/bigquery/bussola_rag.sql",
    "contracts/bigquery/bussola_app.sql",
    "contracts/env.example",
    "contracts/fixtures",
    "data/scripts/aplicar_ddl.py",
    "data/scripts/gerar_fixtures.py",
    "mcp_server/pyproject.toml",
    "mcp_server/Dockerfile",
    "mcp_server/bussola_mcp/contratos.py",
    "mcp_server/bussola_mcp/logging_json.py",
    "mcp_server/bussola_mcp/server.py",
    "mcp_server/bussola_mcp/dominio/interfaces.py",
    "mcp_server/bussola_mcp/dominio/fakes.py",
    "mcp_server/tests/contrato",
    "agent/pyproject.toml",
    "agent/Dockerfile",
    "agent/bussola_agent/estado.py",
    "agent/bussola_agent/callbacks.py",
    "agent/bussola_agent/persistencia.py",
    "agent/bussola_agent/mcp_conexao.py",
    "agent/bussola_agent/extensoes.py",
    "agent/bussola_agent/logging_json.py",
    "agent/bussola_agent/agent.py",
    "agent/tests/contrato",
    "deploy",
]

PADROES_SEGREDO = {
    "chave de API do Google": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "chave privada": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "token OAuth do Google": re.compile(r"ya29\.[0-9A-Za-z_-]{20,}"),
}
# SQL montado por f-string, concatenação, `%` ou `.format` (só vale para texto do usuário/modelo).
SQL_DINAMICO = re.compile(
    r"""(?ix)
    \bf["']+\s*(SELECT|INSERT|UPDATE|DELETE|MERGE)\b
    | ["']\s*(SELECT|INSERT|UPDATE|DELETE|MERGE)\b[^"']*["']\s*(\+|%|\.format\()
    """
)


def _arquivos_do_repo() -> list[Path]:
    try:
        saida = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("não é um repositório git (ex.: dentro da imagem)")
    return [RAIZ / linha for linha in saida.splitlines() if (RAIZ / linha).is_file()]


def _texto(caminho: Path) -> str:
    if caminho.stat().st_size > 1_000_000 or caminho.name == "uv.lock":
        return ""
    return caminho.read_text(encoding="utf-8", errors="ignore")


@pytest.mark.parametrize("relativo", ARTEFATOS_000)
def test_artefatos_do_000_existem(relativo):
    assert (RAIZ / relativo).exists(), relativo


def test_constituicao_tem_os_7_principios_as_secoes_e_nenhum_placeholder():
    texto = (RAIZ / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
    principios = re.findall(r"^### (I|II|III|IV|V|VI|VII)\. .+$", texto, re.MULTILINE)
    assert principios == ["I", "II", "III", "IV", "V", "VI", "VII"]
    for secao in (
        "## Restrições Técnicas e de Plataforma",
        "## Fluxo de Desenvolvimento e Governança",
        "## Governança",
    ):
        assert secao in texto
    assert not re.findall(r"\[[A-Z][A-Z_]{2,}\]", texto)  # nenhum [PLACEHOLDER] do template


def test_mapa_de_contratos_1_nao_cita_web():
    texto = CONTRATOS.read_text(encoding="utf-8")
    mapa = texto.split("## §1", 1)[1].split("## §2", 1)[0]
    assert "web/" not in mapa  # D-002: ADK Web UI, sem front próprio neste PR


def test_env_example_tem_exatamente_as_variaveis_de_contratos_7():
    secao = CONTRATOS.read_text(encoding="utf-8").split("## §7", 1)[1].split("## §8", 1)[0]
    esperadas = set()
    for linha in secao.splitlines():
        if linha.startswith("| `"):
            esperadas |= set(re.findall(r"`([A-Z][A-Z_]+)`", linha.split("|")[1]))
    linhas = (RAIZ / "contracts" / "env.example").read_text(encoding="utf-8").splitlines()
    definidas = {}
    for linha in linhas:
        if re.match(r"^[A-Z][A-Z_]+=", linha):
            nome, _, valor = linha.partition("=")
            definidas[nome] = valor
    assert len(esperadas) == 19
    assert set(definidas) == esperadas
    assert definidas["GOOGLE_API_KEY"] == ""  # só no Plano B; nunca versionar o valor


def test_sem_segredos_nos_arquivos_do_repo():
    achados = []
    for caminho in _arquivos_do_repo():
        texto = _texto(caminho)
        for nome, padrao in PADROES_SEGREDO.items():
            if padrao.search(texto):
                achados.append(f"{caminho.relative_to(RAIZ)}: {nome}")
    assert achados == []


def test_sem_sql_montado_por_concatenacao():
    achados = []
    for caminho in _arquivos_do_repo():
        if caminho.suffix == ".py" and caminho != Path(__file__).resolve():
            if SQL_DINAMICO.search(_texto(caminho)):
                achados.append(str(caminho.relative_to(RAIZ)))
    assert achados == []


@pytest.mark.parametrize(
    "ruim",
    [
        "f\"SELECT * FROM t WHERE id = '{x}'\"",
        "f'''\nSELECT 1'''",
        '"SELECT * FROM t WHERE id = " + x',
        "\"SELECT * FROM t WHERE id = '%s'\" % x",
        '"SELECT {}".format(x)',
    ],
)
def test_detector_de_sql_dinamico_pega_os_casos_ruins(ruim):
    assert SQL_DINAMICO.search(ruim)


def test_detector_de_sql_dinamico_aceita_consulta_parametrizada():
    bom = 'SQL = """\nSELECT a FROM t WHERE id IN UNNEST(@ids)\n"""'
    assert not SQL_DINAMICO.search(bom)
