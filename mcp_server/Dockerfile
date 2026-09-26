# Imagem do bussola-mcp (mock no ciclo 000). Contexto de build = RAIZ do repositório:
#   docker buildx build --platform linux/amd64 -f mcp_server/Dockerfile -t <imagem> .
# (deploy/build_push.sh já faz isso). O mock serve contracts/fixtures/, que fica fora de mcp_server/.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.12 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    BUSSOLA_FIXTURES_DIR=/app/contracts/fixtures \
    PORT=8080

WORKDIR /app
COPY mcp_server/pyproject.toml mcp_server/uv.lock ./
RUN uv sync --frozen --no-dev

COPY mcp_server/bussola_mcp ./bussola_mcp
COPY contracts/fixtures ./contracts/fixtures

EXPOSE 8080
CMD ["python", "-m", "bussola_mcp.server"]
