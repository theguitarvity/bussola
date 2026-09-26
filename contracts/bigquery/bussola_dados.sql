-- bussola_dados: métricas determinísticas (contratos §3). Escrita pelo ciclo 001; leitura por todos.
-- Placeholders {project} e {dataset} são substituídos por data/scripts/aplicar_ddl.py. Idempotente.

CREATE SCHEMA IF NOT EXISTS `{project}.{dataset}` OPTIONS(location="us-central1");

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.perfil_mensal` (
  id_usuario STRING NOT NULL,
  anomes INT64 NOT NULL,
  renda FLOAT64 NOT NULL,
  gasto FLOAT64 NOT NULL,
  sobra FLOAT64 NOT NULL,
  saldo_inicial FLOAT64 NOT NULL,
  saldo_final FLOAT64 NOT NULL,
  saldo_minimo FLOAT64 NOT NULL,
  saldo_maximo FLOAT64 NOT NULL,
  juros FLOAT64 NOT NULL
);

-- Apenas saídas (tipo = 'S').
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.gastos_categoria` (
  id_usuario STRING NOT NULL,
  anomes INT64 NOT NULL,
  macro STRING NOT NULL,
  micro STRING NOT NULL,
  total FLOAT64 NOT NULL,
  qtd INT64 NOT NULL
);

-- Apenas entradas (tipo = 'E'). Base de perfil_financeiro.fontes_renda.
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.entradas_categoria` (
  id_usuario STRING NOT NULL,
  anomes INT64 NOT NULL,
  macro STRING NOT NULL,
  micro STRING NOT NULL,
  total FLOAT64 NOT NULL,
  qtd INT64 NOT NULL
);

-- 1 linha por ocorrência mensal; a agregação respeita ate_anomes na consulta (não vaza o futuro).
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.recorrentes` (
  id_usuario STRING NOT NULL,
  anomes INT64 NOT NULL,
  descr_norm STRING NOT NULL,
  macro STRING NOT NULL,
  micro STRING NOT NULL,
  valor FLOAT64 NOT NULL
);

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.parcelas` (
  id_usuario STRING NOT NULL,
  anomes INT64 NOT NULL,
  descr STRING NOT NULL,
  macro STRING NOT NULL,
  parcela_atual INT64 NOT NULL,
  parcela_total INT64 NOT NULL,
  vlr FLOAT64 NOT NULL
);

-- Seed versionado em data/sql/ (ciclo 001). Base de oportunidades_corte.
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.categorias` (
  macro STRING NOT NULL,
  micro STRING NOT NULL,
  discricionaria BOOL NOT NULL,
  corte_max_pct FLOAT64 NOT NULL
);

-- Agregado (P1). Faixas: ate_3k, 3k_6k, 6k_10k, 10k_20k, acima_20k.
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.referencia_coorte` (
  faixa_renda STRING NOT NULL,
  macro STRING NOT NULL,
  media FLOAT64 NOT NULL,
  mediana FLOAT64 NOT NULL,
  qtd_usuarios INT64 NOT NULL
);
