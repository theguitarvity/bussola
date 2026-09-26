# Smoke manual do agente hello — ciclo 000

**STATUS: PENDENTE — não executado (exige `BUSSOLA_MODEL` validado e credenciais Vertex/GCP).**

Roteiro (AC7), com um integrante que tenha credenciais e depois do `deploy/smoke_modelos.py`:

1. `make mcp` (terminal 1).
2. `export BUSSOLA_MODEL=<id gravado em contracts/env.example>` e `make agent` (terminal 2), abrir a ADK Web UI.
3. Perguntar: **"qual é o meu perfil financeiro?"**
4. Conferir que o agente chama a ferramenta `perfil_financeiro` (o `id_usuario` e o `ate_anomes` vêm do
   `session.state`, quando o 004 os popular; no hello, informe-os na conversa) e que a resposta cita a fonte.
5. Registrar aqui: data, modelo usado, print/trecho do evento `functionCall` de `perfil_financeiro`.

O que **já foi verificado sem LLM** (testes `agent/tests/contrato/`): o `MCPToolset` conecta no mock local e lista as
8 ferramentas; `chamar_ferramenta` força o escopo do `state`; o `root_agent` carrega com os 4 callbacks agregados.
