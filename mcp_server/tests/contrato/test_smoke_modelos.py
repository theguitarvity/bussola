"""smoke_modelos.py (FR-022, AC12): primeiro modelo que responde; nunca imprime a chave."""

from types import SimpleNamespace

import pytest

from ._scripts import carregar

sm = carregar("deploy/smoke_modelos.py")
CHAVE = "AIza" + "B" * 35


def test_escolhe_o_primeiro_candidato_que_responde_e_nao_testa_os_seguintes():
    chamadas = []

    def tentar(modelo):
        chamadas.append(modelo)
        if modelo == "flash-a":
            raise RuntimeError("404 modelo não encontrado")
        return {"latencia_ms": 12}

    escolhido, tentativas = sm.escolher_primeiro(["flash-a", "flash-b", "flash-c"], tentar)
    assert escolhido == "flash-b"
    assert chamadas == ["flash-a", "flash-b"]
    assert [t["modelo"] for t in tentativas] == ["flash-a", "flash-b"]
    assert tentativas[0]["ok"] is False
    assert "404" in tentativas[0]["erro"]
    assert tentativas[1] == {"modelo": "flash-b", "ok": True, "latencia_ms": 12}


def test_nenhum_candidato_responde():
    def tentar(_modelo):
        raise RuntimeError("sem acesso")

    escolhido, tentativas = sm.escolher_primeiro(["a", "b"], tentar)
    assert escolhido is None
    assert [t["ok"] for t in tentativas] == [False, False]


def test_atualizar_env_preenche_so_as_chaves_pedidas_e_preserva_o_resto():
    texto = "# comentário\nBUSSOLA_MODEL=\nEMBEDDING_MODEL=\nOUTRA=1\n"
    novo = sm.atualizar_env(texto, {"BUSSOLA_MODEL": "gemini-x"})
    assert novo == "# comentário\nBUSSOLA_MODEL=gemini-x\nEMBEDDING_MODEL=\nOUTRA=1\n"
    assert sm.atualizar_env(novo, {"EMBEDDING_MODEL": "emb-y"}).count("emb-y") == 1


def test_atualizar_env_com_chave_ausente_e_erro():
    with pytest.raises(KeyError):
        sm.atualizar_env("A=1\n", {"BUSSOLA_MODEL": "x"})


def test_sanitizar_remove_chaves_e_tokens_e_limita_o_tamanho():
    texto = f"falhou com a chave {CHAVE} e o token ya29.{'c' * 30} " + "x" * 500
    limpo = sm.sanitizar(texto)
    assert CHAVE not in limpo
    assert "ya29." not in limpo
    assert len(limpo) <= 200


def test_relatorio_lista_modelos_latencia_e_dimensao_sem_segredos():
    md = sm.relatorio_md(
        projeto="batalha-time-07-lkbv",
        regiao="us-central1",
        caminho="vertex",
        flash=(
            "flash-b",
            [
                {"modelo": "flash-a", "ok": False, "erro": "404"},
                {"modelo": "flash-b", "ok": True, "latencia_ms": 12},
            ],
        ),
        embedding=("emb-y", [{"modelo": "emb-y", "ok": True, "latencia_ms": 30, "dimensao": 768}]),
    )
    for esperado in ("flash-a", "flash-b", "emb-y", "12", "30", "768", "dimensão", "vertex"):
        assert esperado in md
    assert "AIza" not in md


def test_chave_do_secret_manager_e_lida_em_memoria_e_nunca_impressa(monkeypatch, capsys):
    pedidos = []

    def falso(*args, **kwargs):
        pedidos.append((args, kwargs))
        return SimpleNamespace(stdout=CHAVE + "\n", returncode=0)

    monkeypatch.setattr(sm.subprocess, "run", falso)
    chave = sm.ler_chave_secret_manager("meu-projeto")
    saida = capsys.readouterr()
    assert chave == CHAVE
    assert CHAVE not in saida.out + saida.err
    assert pedidos[0][1].get("capture_output") is True  # o valor nunca vai para o terminal
