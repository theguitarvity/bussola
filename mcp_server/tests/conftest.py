"""Configuração comum dos testes: modo fake ligado e sem rede (só loopback)."""

import os
import socket

import pytest

os.environ.setdefault("BUSSOLA_FAKES", "TRUE")

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_connect_original = socket.socket.connect


@pytest.fixture(autouse=True)
def _sem_rede(request, monkeypatch):
    """Falha qualquer conexão fora de loopback, exceto nos testes marcados `bq`."""
    if request.node.get_closest_marker("bq"):
        return

    def connect(self, address):
        if isinstance(address, tuple) and address[0] not in _LOOPBACK:
            raise RuntimeError(f"teste tentou acessar a rede: {address[0]}")
        return _connect_original(self, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
