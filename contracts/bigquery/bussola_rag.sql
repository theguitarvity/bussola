-- bussola_rag: corpus do RAG (contratos §3). Escrita pelo ciclo 002.
-- tipo: ficha_mensal (P0), perfil_anual (P0, gravado com anomes = 202512), coorte (P1, id_usuario NULL), lancamento (P2).
-- Filtro obrigatório na busca:
--   (id_usuario = @id_usuario OR tipo = 'coorte') AND (anomes IS NULL OR anomes <= @ate_anomes)

CREATE SCHEMA IF NOT EXISTS `{project}.{dataset}` OPTIONS(location="us-central1");

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.documentos` (
  doc_id STRING NOT NULL,
  id_usuario STRING,
  tipo STRING NOT NULL,
  anomes INT64,
  texto STRING NOT NULL,
  fonte JSON NOT NULL,
  embedding ARRAY<FLOAT64>,
  modelo_embedding STRING NOT NULL,
  gerado_em TIMESTAMP NOT NULL
);
