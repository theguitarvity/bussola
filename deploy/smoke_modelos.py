"""Valida os IDs de modelo (Gemini Flash e embedding) e os grava (ciclo 000; FR-022).

Tenta os candidatos, em ordem, via Vertex (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`) com as credenciais
do integrante; o primeiro que responde vence. Grava `BUSSOLA_MODEL` e `EMBEDDING_MODEL` em
`contracts/env.example` e o relatório (modelos testados, latência, dimensão do embedding) em
`specs/000-fundacao-contratos/modelos.md`. Os candidatos são SUPOSIÇÕES derivadas do Model Garden
(mestre §5): só valem depois de responderem aqui.

    uv run --project agent python deploy/smoke_modelos.py [--fallback-api]

Se nenhum Flash responder via Vertex, `--fallback-api` testa a Gemini API com a chave do Secret
Manager (`gemini-api-key`), lida em memória via `gcloud` e NUNCA impressa. Erros são sanitizados.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FLASH_PADRAO = ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash")
EMBEDDING_PADRAO = ("gemini-embedding-001", "text-embedding-005")
PROJETO_PADRAO = "batalha-time-07-lkbv"
REGIAO_PADRAO = "us-central1"
SEGREDO = "gemini-api-key"

_SEGREDOS = (
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "[chave removida]"),
    (re.compile(r"ya29\.[0-9A-Za-z_-]+"), "[token removido]"),
    (re.compile(r"Bearer\s+\S+", re.IGNORECASE), "Bearer [removido]"),
)


def sanitizar(texto: str, limite: int = 200) -> str:
    """Remove chaves/tokens e limita o tamanho: só isto pode ir para logs e relatórios."""
    for padrao, troca in _SEGREDOS:
        texto = padrao.sub(troca, texto)
    return " ".join(texto.split())[:limite]


def escolher_primeiro(candidatos, tentar):
    """Tenta cada candidato em ordem e para no primeiro que responde.

    `tentar(modelo)` devolve um dict (ex.: `{"latencia_ms": 12}`) ou levanta. Retorna
    `(escolhido | None, tentativas)`, com um dict por candidato efetivamente testado.
    """
    tentativas = []
    for modelo in candidatos:
        try:
            tentativas.append({"modelo": modelo, "ok": True, **tentar(modelo)})
            return modelo, tentativas
        except Exception as erro:  # qualquer falha (404, permissão, cota) é só "não respondeu"
            tentativas.append({"modelo": modelo, "ok": False, "erro": sanitizar(str(erro))})
    return None, tentativas


def atualizar_env(texto: str, valores: dict[str, str]) -> str:
    """Preenche `CHAVE=` em `texto` (formato de contracts/env.example), preservando o resto."""
    for chave, valor in valores.items():
        padrao = re.compile(rf"^{re.escape(chave)}=.*$", re.MULTILINE)
        if not padrao.search(texto):
            raise KeyError(chave)
        texto = padrao.sub(lambda _m, c=chave, v=valor: f"{c}={v}", texto)
    return texto


def ler_chave_secret_manager(projeto: str) -> str:
    """Lê `gemini-api-key` do Secret Manager em memória; o valor nunca é impresso."""
    comando = [
        "gcloud",
        "secrets",
        "versions",
        "access",
        "latest",
        f"--secret={SEGREDO}",
        f"--project={projeto}",
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(sanitizar(resultado.stderr))
    return resultado.stdout.strip()


def relatorio_md(projeto: str, regiao: str, caminho: str, flash, embedding) -> str:
    """Markdown de `specs/000-fundacao-contratos/modelos.md` (sem segredos)."""

    def linhas(escolhido, tentativas):
        saida = ["| Modelo | Resultado | Latência (ms) | Dimensão |", "|---|---|---|---|"]
        for t in tentativas:
            resultado = "respondeu" if t["ok"] else f"falhou: {t['erro']}"
            latencia = t.get("latencia_ms", "—")
            dimensao = t.get("dimensao", "—")
            saida.append(f"| `{t['modelo']}` | {resultado} | {latencia} | {dimensao} |")
        saida.append("")
        saida.append(f"Escolhido: `{escolhido}`" if escolhido else "Escolhido: **nenhum**")
        return saida

    return "\n".join(
        [
            "# Modelos validados — ciclo 000",
            "",
            f"Gerado por `deploy/smoke_modelos.py` em {datetime.now(UTC):%Y-%m-%d %H:%M} UTC.",
            f"Projeto `{projeto}`, região `{regiao}`, caminho: **{caminho}**.",
            "",
            "## Gemini Flash",
            "",
            *linhas(*flash),
            "",
            "## Embedding (a dimensão do vetor está na coluna Dimensão)",
            "",
            *linhas(*embedding),
            "",
        ]
    )


def _tentar_flash(cliente, modelo: str) -> dict:
    inicio = time.perf_counter()
    cliente.models.generate_content(model=modelo, contents="Responda apenas: ok")
    return {"latencia_ms": round((time.perf_counter() - inicio) * 1000)}


def _tentar_embedding(cliente, modelo: str) -> dict:
    inicio = time.perf_counter()
    resposta = cliente.models.embed_content(model=modelo, contents="teste de embedding")
    return {
        "latencia_ms": round((time.perf_counter() - inicio) * 1000),
        "dimensao": len(resposta.embeddings[0].values),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projeto", default=os.environ.get("GOOGLE_CLOUD_PROJECT", PROJETO_PADRAO))
    ap.add_argument("--regiao", default=os.environ.get("GOOGLE_CLOUD_LOCATION", REGIAO_PADRAO))
    ap.add_argument("--flash", nargs="+", default=list(FLASH_PADRAO), help="candidatos Flash")
    ap.add_argument("--embedding", nargs="+", default=list(EMBEDDING_PADRAO))
    ap.add_argument("--fallback-api", action="store_true", help="se nenhum Flash responder")
    ap.add_argument("--env", type=Path, default=RAIZ / "contracts" / "env.example")
    ap.add_argument(
        "--relatorio",
        type=Path,
        default=RAIZ / "specs" / "000-fundacao-contratos" / "modelos.md",
    )
    args = ap.parse_args(argv)

    from google import genai

    cliente = genai.Client(vertexai=True, project=args.projeto, location=args.regiao)
    caminho = "vertex"
    flash = escolher_primeiro(args.flash, lambda m: _tentar_flash(cliente, m))
    if flash[0] is None and args.fallback_api:
        cliente = genai.Client(api_key=ler_chave_secret_manager(args.projeto))
        caminho = "gemini_api (Plano B: GOOGLE_GENAI_USE_VERTEXAI=FALSE + GOOGLE_API_KEY)"
        flash = escolher_primeiro(args.flash, lambda m: _tentar_flash(cliente, m))
    embedding = escolher_primeiro(args.embedding, lambda m: _tentar_embedding(cliente, m))

    achados = (("BUSSOLA_MODEL", flash[0]), ("EMBEDDING_MODEL", embedding[0]))
    valores = {chave: modelo for chave, modelo in achados if modelo}
    if valores:
        texto = atualizar_env(args.env.read_text(encoding="utf-8"), valores)
        args.env.write_text(texto, encoding="utf-8")
    relatorio = relatorio_md(args.projeto, args.regiao, caminho, flash, embedding)
    args.relatorio.write_text(relatorio, encoding="utf-8")
    print(f"BUSSOLA_MODEL={flash[0] or '(nenhum respondeu)'}")
    print(f"EMBEDDING_MODEL={embedding[0] or '(nenhum respondeu)'}")
    print(f"relatório: {args.relatorio}")
    return 0 if flash[0] and embedding[0] else 1


if __name__ == "__main__":
    sys.exit(main())
