-- bussola_app: estado de aplicação (contratos §3). Escrita pelos ciclos 005/006 (streaming insert).
-- O mesmo DDL cria bussola_app_dev, o ÚNICO dataset onde os testes gravam.

CREATE SCHEMA IF NOT EXISTS `{project}.{dataset}` OPTIONS(location="us-central1");

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.planos` (
  plano_id STRING NOT NULL,
  session_id STRING NOT NULL,
  id_usuario STRING NOT NULL,
  objetivo STRING NOT NULL,
  valor_alvo FLOAT64 NOT NULL,
  prazo_meses INT64 NOT NULL,
  cenario STRING NOT NULL,
  aporte_mensal FLOAT64 NOT NULL,
  ate_anomes INT64 NOT NULL,
  criado_em TIMESTAMP NOT NULL
);

-- decisao: 'aceito' | 'recusado'
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.consentimentos` (
  consent_id STRING NOT NULL,
  session_id STRING NOT NULL,
  plano_id STRING,
  acao STRING NOT NULL,
  decisao STRING NOT NULL,
  texto_apresentado STRING NOT NULL,
  ts TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.auditoria` (
  evento_id STRING NOT NULL,
  session_id STRING NOT NULL,
  estado STRING NOT NULL,
  tipo_evento STRING NOT NULL,
  ferramenta STRING,
  resumo JSON NOT NULL,
  ts TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.acompanhamento` (
  plano_id STRING NOT NULL,
  anomes INT64 NOT NULL,
  planejado FLOAT64 NOT NULL,
  realizado FLOAT64 NOT NULL,
  desvio FLOAT64 NOT NULL,
  categoria_desvio STRING,
  acao_sugerida STRING,
  ts TIMESTAMP NOT NULL
);
