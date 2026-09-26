# Imagem do bussola-agent (agente hello no ciclo 000), servida pela ADK Web UI.
# Contexto de build = RAIZ do repositório:
#   docker buildx build --platform linux/amd64 -f agent/Dockerfile -t <imagem> .
# O `adk web` NÃO tem autenticação própria: o serviço é publicado privado (Cloud Run IAM).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.12 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

WORKDIR /app
COPY agent/pyproject.toml agent/uv.lock ./
RUN uv sync --frozen --no-dev

COPY agent/bussola_agent ./bussola_agent

EXPOSE 8080
# BUSSOLA_MODEL, MCP_URL, MCP_USE_OIDC etc. vêm do ambiente do Cloud Run (deploy/deploy.sh).
CMD ["sh", "-c", "adk web --host 0.0.0.0 --port ${PORT:-8080} ."]
