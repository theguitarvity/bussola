#!/usr/bin/env bash
# Publica um serviço no Cloud Run a partir da imagem enviada por deploy/build_push.sh (mesmo SHA).
#
# Uso:  deploy/deploy.sh <bussola-mcp|bussola-agent> [--tag cNNN] [--no-traffic]
#       (DRY_RUN=1 só imprime os comandos)
# Regras do projeto (constituição VII): SEMPRE `--tag cNNN --no-traffic` (padrão c000; `--no-traffic`
# já é o padrão e é aceito por compatibilidade) — só o ciclo 007 move tráfego. Os dois serviços
# saem PRIVADOS (`--no-allow-unauthenticated`); tornar o agente público é decisão do 007 (o `adk web`
# não tem autenticação própria). Sem --service-account: usa a SA default do Compute (Plano A/B).
#
# Se o gcloud recusar `--no-traffic` ao CRIAR um serviço novo (não verificado; sem gcloud no
# desenvolvimento), o script cria o serviço sem a flag, avisa, e o desvio deve ser registrado em
# specs/000-fundacao-contratos/deploy.md.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-batalha-time-07-lkbv}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
REPO="agentes"
SA_DEFAULT="1061873050224-compute@developer.gserviceaccount.com"

uso() { echo "Uso: $0 <bussola-mcp|bussola-agent> [--tag cNNN] [--no-traffic]" >&2; exit 2; }

[ $# -ge 1 ] || uso
SERVICO="$1"
shift
case "$SERVICO" in bussola-mcp | bussola-agent) ;; *) uso ;; esac

TAG="c000"
while [ $# -gt 0 ]; do
  case "$1" in
    --tag) [ $# -ge 2 ] || uso; TAG="$2"; shift 2 ;;
    --no-traffic) shift ;;
    *) uso ;;
  esac
done
[[ "$TAG" =~ ^c[0-9]{3}$ ]] || { echo "ERRO: --tag deve ser cNNN (ex.: c000)." >&2; exit 2; }

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"
IMAGEM="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICO}:$(git rev-parse --short HEAD)"
executar() { echo "+ $*"; [ "${DRY_RUN:-}" = "1" ] || "$@"; }

ARGS=(run deploy "$SERVICO" --image "$IMAGEM" --region "$REGION" --project "$PROJECT"
  --no-allow-unauthenticated --tag "$TAG" --no-traffic)

if [ "$SERVICO" = "bussola-agent" ]; then
  MODELO="${BUSSOLA_MODEL:-$(sed -n 's/^BUSSOLA_MODEL=//p' contracts/env.example)}"
  if [ -z "$MODELO" ]; then
    echo "ERRO: BUSSOLA_MODEL vazio. Rode deploy/smoke_modelos.py (grava em contracts/env.example) ou exporte BUSSOLA_MODEL." >&2
    exit 1
  fi
  if [ "${DRY_RUN:-}" = "1" ]; then
    MCP_URL="https://<url-do-bussola-mcp>/mcp"
  else
    URL_MCP="$(gcloud run services describe bussola-mcp --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
    [ -n "$URL_MCP" ] || { echo "ERRO: publique o bussola-mcp antes do agente." >&2; exit 1; }
    MCP_URL="${URL_MCP}/mcp"
  fi
  ARGS+=(--max-instances=1 --set-env-vars
    "MCP_URL=${MCP_URL},MCP_USE_OIDC=TRUE,GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},BUSSOLA_MODEL=${MODELO}")
fi

if [ "${DRY_RUN:-}" = "1" ]; then
  executar gcloud "${ARGS[@]}"
  echo "(DRY_RUN=1: nada foi executado)"
  exit 0
fi

if ! saida="$(gcloud "${ARGS[@]}" 2>&1)"; then
  echo "$saida" >&2
  if grep -qi -- 'no-traffic' <<<"$saida"; then
    echo "AVISO: o gcloud recusou --no-traffic; criando o serviço SEM a flag. Registre o desvio em specs/000-fundacao-contratos/deploy.md." >&2
    SEM=()
    for a in "${ARGS[@]}"; do [ "$a" = "--no-traffic" ] || SEM+=("$a"); done
    gcloud "${SEM[@]}"
  else
    exit 1
  fi
else
  echo "$saida"
fi

# Verificação: sem token = recusado; com ID token do integrante = aceito.
URL="$(gcloud run services describe "$SERVICO" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
ALVO="${URL/https:\/\//https://${TAG}---}"
[ "$SERVICO" = "bussola-mcp" ] && CAMINHO="/mcp" || CAMINHO="/list-apps"
sem_token="$(curl -s -o /dev/null -w '%{http_code}' "${ALVO}${CAMINHO}" || true)"
com_token="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $(gcloud auth print-identity-token)" "${ALVO}${CAMINHO}" || true)"
echo "Verificação ${ALVO}${CAMINHO}: sem token -> ${sem_token} (esperado 401/403); com ID token -> ${com_token} (esperado != 401/403)."

if [ "$SERVICO" = "bussola-mcp" ]; then
  echo "PRÓXIMO PASSO (confirmação humana; não executado aqui): permitir que a SA do agente chame o MCP:"
  echo "  gcloud run services add-iam-policy-binding bussola-mcp --region ${REGION} --project ${PROJECT} \\"
  echo "    --member=serviceAccount:${SA_DEFAULT} --role=roles/run.invoker"
fi
