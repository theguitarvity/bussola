#!/usr/bin/env bash
# Plano B de IAM em nível de DATASET para a service account default do Compute (mestre §16).
#
#   dataViewer em bussola_dados e bussola_rag; dataEditor em bussola_app e bussola_app_dev.
#
# EXIGE CONFIRMAÇÃO HUMANA: o script imprime o plano e só executa depois que uma pessoa digita
# CONFIRMO em um terminal (lido de /dev/tty). Não existe flag nem variável que dispense isso, de
# propósito: quem chama (inclusive um agente) não consegue aprovar por conta própria.
# DRY_RUN=1 só imprime os comandos e não pergunta nada.
#
# As concessões usam o DCL do BigQuery (GRANT ... ON SCHEMA) via `bq query`; a sintaxe não foi
# verificada aqui (sem bq/gcloud no ambiente de desenvolvimento) — confira na primeira execução.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-batalha-time-07-lkbv}"
MEMBRO="serviceAccount:1061873050224-compute@developer.gserviceaccount.com"
CONCESSOES=(
  "bussola_dados:roles/bigquery.dataViewer"
  "bussola_rag:roles/bigquery.dataViewer"
  "bussola_app:roles/bigquery.dataEditor"
  "bussola_app_dev:roles/bigquery.dataEditor"
)

sql_da_concessao() {
  local dataset="${1%%:*}" papel="${1##*:}"
  echo "GRANT \`${papel}\` ON SCHEMA \`${PROJECT}.${dataset}\` TO \"${MEMBRO}\""
}

echo "Plano B de IAM (projeto ${PROJECT}), membro ${MEMBRO}:"
for c in "${CONCESSOES[@]}"; do
  echo "  bq query --nouse_legacy_sql --project_id=${PROJECT} '$(sql_da_concessao "$c")'"
done

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "(DRY_RUN=1: nada foi executado)"
  exit 0
fi

if ! { read -r -p "Digite CONFIRMO para aplicar estas concessões: " resposta < /dev/tty; } 2> /dev/null; then
  echo "ERRO: a confirmação humana exige um terminal (/dev/tty). Nada foi executado." >&2
  exit 1
fi
if [ "$resposta" != "CONFIRMO" ]; then
  echo "Cancelado. Nada foi executado."
  exit 1
fi

for c in "${CONCESSOES[@]}"; do
  bq query --nouse_legacy_sql --project_id="${PROJECT}" "$(sql_da_concessao "$c")"
done
echo "Concessões aplicadas."
