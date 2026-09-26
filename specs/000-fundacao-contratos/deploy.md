# Pipeline de deploy — ciclo 000

**STATUS: PARCIAL.** Validado localmente com Docker; **publicação no Artifact Registry e no Cloud Run: PENDENTE**
(sem `gcloud`/credenciais no ambiente de desenvolvimento).

## Verificado localmente (2026-09-26, Docker 29.8 + buildx 0.37, host linux/amd64)

| Item | Resultado |
|---|---|
| `docker build --platform linux/amd64 -f mcp_server/Dockerfile .` | ok (contexto = raiz; `uv sync --frozen --no-dev`) |
| Contêiner do MCP com `PORT=8080` | lista as 8 ferramentas; golden `__ate_202506` com aviso de mock; `ENTRADA_INVALIDA` e `USUARIO_INEXISTENTE`; logs em JSON (Cloud Logging) |
| `docker build --platform linux/amd64 -f agent/Dockerfile .` | ok |
| Contêiner do agente (`adk web --host 0.0.0.0 --port $PORT .`) | sobe e `GET /list-apps` → `["bussola_agent"]` |
| MCP com `Host: *.run.app` | aceito (200), não há bloqueio de host pelo FastMCP |
| Achado | O `adk web` **não falha no start** sem `BUSSOLA_MODEL`: só erra ao carregar o agente. O `deploy.sh` do agente aborta se o modelo estiver vazio |
| Achado | O `adk web` avisa que seus endpoints **não têm autenticação**: os serviços saem privados; tornar público é decisão do 007 |

## Pendente (integrante com `gcloud` autenticado)

```bash
gcloud auth login && gcloud auth configure-docker us-central1-docker.pkg.dev
deploy/build_push.sh bussola-mcp && deploy/build_push.sh bussola-agent
deploy/deploy.sh bussola-mcp        # sempre --tag c000 --no-traffic (privado)
deploy/deploy.sh bussola-agent      # exige BUSSOLA_MODEL (smoke_modelos.py)
```

Registrar aqui, depois de executar:

- [ ] Imagens no AR `agentes` (`us-central1-docker.pkg.dev/batalha-time-07-lkbv/agentes/...`).
- [ ] O `gcloud` aceitou `--no-traffic` ao **criar** os serviços? Se recusou, o `deploy.sh` criou sem a flag: anotar como
      **desvio da constituição VII** (research R14, não verificado).
- [ ] MCP privado: sem token → 401/403; com `gcloud auth print-identity-token` de um integrante → aceito.
- [ ] Chamada do agente ao MCP com a SA default (`run.invoker` concedido? passo impresso pelo `deploy.sh`) e a chamada ao
      Gemini pelo Cloud Run com a SA default (espera-se **falhar** por falta de IAM: alimenta a decisão Plano A/B).
- [ ] `GRANT` de `deploy/iam_datasets.sh` (sintaxe não verificada) funcionou.
