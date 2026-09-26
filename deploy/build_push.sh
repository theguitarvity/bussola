#!/usr/bin/env bash
# Constrói a imagem de um serviço (linux/amd64) e a envia ao Artifact Registry `agentes`.
#
# Uso:  deploy/build_push.sh <bussola-mcp|bussola-agent>       (DRY_RUN=1 só imprime os comandos)
# Pré-requisitos (uma vez por máquina):
#   gcloud auth login && gcloud auth configure-docker us-central1-docker.pkg.dev
# A tag é o SHA curto do commit atual. O contexto de build é a RAIZ do repositório (o mock do MCP
# copia contracts/fixtures/, que fica fora de mcp_server/). Não usamos `gcloud run deploy --source`
# nem `adk deploy`: exigem bucket de staging, que o time não pode criar.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-batalha-time-07-lkbv}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
REPO="agentes"

uso() { echo "Uso: $0 <bussola-mcp|bussola-agent>" >&2; exit 2; }

[ $# -eq 1 ] || uso
case "$1" in
  bussola-mcp) DIR="mcp_server" ;;
  bussola-agent) DIR="agent" ;;
  *) uso ;;
esac

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"
TAG="$(git rev-parse --short HEAD)"
IMAGEM="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/$1:${TAG}"

if [ -n "$(git status --porcelain)" ]; then
  echo "AVISO: há alterações não commitadas; a tag ${TAG} não identifica só o commit." >&2
fi

executar() { echo "+ $*"; [ "${DRY_RUN:-}" = "1" ] || "$@"; }

executar docker buildx build --platform linux/amd64 -f "${DIR}/Dockerfile" -t "$IMAGEM" --push .
echo "$IMAGEM"
