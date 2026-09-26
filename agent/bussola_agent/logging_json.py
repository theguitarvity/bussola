"""Logs estruturados em JSON, uma linha por evento em stdout (contratos §9).

Compatível com Cloud Logging. Só os campos de `CAMPOS_PERMITIDOS` são emitidos: qualquer outro
(prompt, texto de lançamento, chave, token...) é descartado. Nunca passe conteúdo sensível em
`evento`. Este arquivo é idêntico nos dois serviços (mcp_server e agent), de propósito: eles são
projetos independentes.
"""

import json
import logging
import os
import sys

CAMPOS_PERMITIDOS = frozenset(
    {
        "servico",
        "session_id",
        "estado_jornada",
        "ferramenta",
        "evento",
        "consentimento",
        "ate_anomes",
        "latencia_ms",
        "erro_codigo",
    }
)

_logger = logging.getLogger("bussola")
_servico = "desconhecido"


class _FormatadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        linha = {"severity": record.levelname, "message": record.getMessage()}
        for campo in sorted(CAMPOS_PERMITIDOS):
            valor = getattr(record, campo, None)
            if valor is not None:
                linha[campo] = valor
        return json.dumps(linha, ensure_ascii=False)


class _HandlerStdout(logging.StreamHandler):
    """Escreve no `sys.stdout` do momento (útil quando o stdout é trocado, como nos testes)."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(_FormatadorJson())

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _valor) -> None:
        pass


def configurar(servico: str) -> None:
    """Define o nome do serviço e o nível (`LOG_LEVEL`, padrão INFO). Pode ser chamada de novo."""
    global _servico
    _servico = servico
    if not _logger.handlers:
        _logger.addHandler(_HandlerStdout())
    _logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    _logger.propagate = False


def log_evento(evento: str, *, nivel: int = logging.INFO, **campos) -> None:
    """Emite uma linha JSON. Campos fora de `CAMPOS_PERMITIDOS` são descartados."""
    extra = {k: v for k, v in campos.items() if k in CAMPOS_PERMITIDOS}
    extra["servico"] = _servico
    extra["evento"] = evento
    _logger.log(nivel, evento, extra=extra)
