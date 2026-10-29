-- 13/10/2026: banco de Ads (tráfego pago) — as 7 abas da planilha de Ads viram
-- tabelas. Quem grava é o processo do time de pago, pela porta /api/ads/<tabela>
-- (docs/ads-banco-api.md). Uma linha por item por dia (mesmo formato da planilha).
-- Só os números BRUTOS são gravados; as taxas (CTR, CPC, CPM, CPA, CPLQ,
-- Connect Rate, Hook Rate, Frequência, Taxa de conversão) são GENERATED — o
-- banco calcula, com as mesmas fórmulas da planilha (conferidas linha a linha).
-- Porcentagens em escala 0–100. Dinheiro em reais (REAL).

-- ---------- Meta Ads ----------
CREATE TABLE IF NOT EXISTS ads_meta_campanhas (
  id                 TEXT NOT NULL,        -- ID da campanha (ex. m1)
  data               TEXT NOT NULL,        -- AAAA-MM-DD
  campanha           TEXT NOT NULL,
  nome_exibicao      TEXT,
  objetivo           TEXT,
  destino_link       INTEGER CHECK (destino_link IN (0, 1)),  -- "DESTINO LINK?" SIM=1 / NÃO=0 (Connect Rate só vale com 1)
  impressoes         INTEGER,
  cliques            INTEGER,              -- cliques no link
  page_view          INTEGER,
  leads              INTEGER,
  leads_qualificados INTEGER,
  leads_fechados     INTEGER,
  investimento       REAL,
  ctr_pct            REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  connect_rate_pct   REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(page_view * 100.0 / cliques, 2) END) VIRTUAL,
  taxa_conversao_pct REAL GENERATED ALWAYS AS (CASE WHEN page_view > 0 THEN ROUND(leads * 100.0 / page_view, 2) END) VIRTUAL,
  cpc                REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpm                REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(investimento * 1000.0 / impressoes, 2) END) VIRTUAL,
  cpa                REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  cplq               REAL GENERATED ALWAYS AS (CASE WHEN leads_qualificados > 0 THEN ROUND(investimento / leads_qualificados, 2) END) VIRTUAL,
  atualizacao        TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, data)
);

CREATE TABLE IF NOT EXISTS ads_meta_conjuntos (
  id                 TEXT NOT NULL,        -- ID do conjunto (ex. m1.1)
  data               TEXT NOT NULL,
  campanha           TEXT NOT NULL,
  conjunto           TEXT NOT NULL,
  nome_exibicao      TEXT,
  nivel_publico      TEXT,                 -- FRIO, MORNO, QUENTE…
  impressoes         INTEGER,
  alcance            INTEGER,
  cliques            INTEGER,
  page_view          INTEGER,
  leads              INTEGER,
  leads_qualificados INTEGER,
  leads_fechados     INTEGER,
  investimento       REAL,
  ctr_pct            REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  frequencia         REAL GENERATED ALWAYS AS (CASE WHEN alcance > 0 THEN ROUND(impressoes * 1.0 / alcance, 2) END) VIRTUAL,
  connect_rate_pct   REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(page_view * 100.0 / cliques, 2) END) VIRTUAL,
  taxa_conversao_pct REAL GENERATED ALWAYS AS (CASE WHEN page_view > 0 THEN ROUND(leads * 100.0 / page_view, 2) END) VIRTUAL,
  cpc                REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpm                REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(investimento * 1000.0 / impressoes, 2) END) VIRTUAL,
  cpa                REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  cplq               REAL GENERATED ALWAYS AS (CASE WHEN leads_qualificados > 0 THEN ROUND(investimento / leads_qualificados, 2) END) VIRTUAL,
  atualizacao        TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, data)
);

CREATE TABLE IF NOT EXISTS ads_meta_anuncios (
  id                 TEXT NOT NULL,        -- ID do anúncio (ex. m1.1.1)
  data               TEXT NOT NULL,
  campanha           TEXT NOT NULL,
  conjunto           TEXT NOT NULL,
  anuncio            TEXT NOT NULL,        -- nome do anúncio (liga com a Biblioteca de Criativos)
  nome_exibicao      TEXT,
  impressoes         INTEGER,
  alcance            INTEGER,
  cliques            INTEGER,
  reproducoes_3s     INTEGER,
  leads              INTEGER,
  leads_qualificados INTEGER,
  leads_fechados     INTEGER,
  investimento       REAL,
  ctr_pct            REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  hook_rate_pct      REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(reproducoes_3s * 100.0 / impressoes, 2) END) VIRTUAL,
  cpc                REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpm                REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(investimento * 1000.0 / impressoes, 2) END) VIRTUAL,
  cpa                REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  cplq               REAL GENERATED ALWAYS AS (CASE WHEN leads_qualificados > 0 THEN ROUND(investimento / leads_qualificados, 2) END) VIRTUAL,
  atualizacao        TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, data)
);

-- ---------- Google Ads ----------
CREATE TABLE IF NOT EXISTS ads_google_campanhas (
  id                          TEXT NOT NULL,   -- ex. g1
  data                        TEXT NOT NULL,
  campanha                    TEXT NOT NULL,
  nome_exibicao               TEXT,
  objetivo                    TEXT,
  impressoes                  INTEGER,
  cliques                     INTEGER,
  page_view                   INTEGER,
  leads                       INTEGER,
  leads_qualificados          INTEGER,
  leads_fechados              INTEGER,
  parcela_impressoes_pct      REAL,            -- vem pronto da API (search impression share)
  parc_perdida_orcamento_pct  REAL,
  parc_perdida_classif_pct    REAL,
  investimento                REAL,
  ctr_pct            REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  connect_rate_pct   REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(page_view * 100.0 / cliques, 2) END) VIRTUAL,
  taxa_conversao_pct REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(leads * 100.0 / cliques, 2) END) VIRTUAL,
  cpc                REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpm                REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(investimento * 1000.0 / impressoes, 2) END) VIRTUAL,
  cpa                REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  cplq               REAL GENERATED ALWAYS AS (CASE WHEN leads_qualificados > 0 THEN ROUND(investimento / leads_qualificados, 2) END) VIRTUAL,
  atualizacao        TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, data)
);

CREATE TABLE IF NOT EXISTS ads_google_grupos (
  id                          TEXT NOT NULL,   -- ex. g1.1
  data                        TEXT NOT NULL,
  campanha                    TEXT NOT NULL,
  grupo                       TEXT NOT NULL,   -- grupo de anúncio
  nome_exibicao               TEXT,
  impressoes                  INTEGER,
  cliques                     INTEGER,
  page_view                   INTEGER,
  leads                       INTEGER,
  leads_qualificados          INTEGER,
  leads_fechados              INTEGER,
  nivel_qualidade             REAL,            -- 1–10
  indice_exp_usuario          TEXT,            -- ABAIXO DA MÉDIA / MÉDIA / ACIMA DA MÉDIA
  indice_relev_anuncio        TEXT,
  indice_ctr_esperado         TEXT,
  parcela_impressoes_pct      REAL,
  parc_perdida_orcamento_pct  REAL,
  parc_perdida_classif_pct    REAL,
  investimento                REAL,
  ctr_pct            REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  connect_rate_pct   REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(page_view * 100.0 / cliques, 2) END) VIRTUAL,
  taxa_conversao_pct REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(leads * 100.0 / cliques, 2) END) VIRTUAL,
  cpc                REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpm                REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(investimento * 1000.0 / impressoes, 2) END) VIRTUAL,
  cpa                REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  cplq               REAL GENERATED ALWAYS AS (CASE WHEN leads_qualificados > 0 THEN ROUND(investimento / leads_qualificados, 2) END) VIRTUAL,
  atualizacao        TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, data)
);

CREATE TABLE IF NOT EXISTS ads_google_termos (
  data          TEXT NOT NULL,
  termo         TEXT NOT NULL,                 -- termo de pesquisa
  campanha      TEXT NOT NULL,
  grupo         TEXT NOT NULL,
  impressoes    INTEGER,
  cliques       INTEGER,
  leads         INTEGER,
  investimento  REAL,
  ctr_pct       REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  cpc           REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpa           REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  atualizacao   TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (data, termo, campanha, grupo)   -- termo não tem ID próprio
);

CREATE TABLE IF NOT EXISTS ads_google_palavras (
  id                    TEXT NOT NULL,         -- ex. g1.1.1
  data                  TEXT NOT NULL,
  campanha              TEXT NOT NULL,
  grupo                 TEXT NOT NULL,
  palavra_chave         TEXT NOT NULL,
  tipo_correspondencia  TEXT,                  -- AMPLA, FRASE, EXATA
  impressoes            INTEGER,
  cliques               INTEGER,
  leads                 INTEGER,
  leads_qualificados    INTEGER,
  leads_fechados        INTEGER,
  nivel_qualidade       REAL,
  investimento          REAL,
  ctr_pct       REAL GENERATED ALWAYS AS (CASE WHEN impressoes > 0 THEN ROUND(cliques * 100.0 / impressoes, 2) END) VIRTUAL,
  cpc           REAL GENERATED ALWAYS AS (CASE WHEN cliques > 0 THEN ROUND(investimento / cliques, 2) END) VIRTUAL,
  cpa           REAL GENERATED ALWAYS AS (CASE WHEN leads > 0 THEN ROUND(investimento / leads, 2) END) VIRTUAL,
  cplq          REAL GENERATED ALWAYS AS (CASE WHEN leads_qualificados > 0 THEN ROUND(investimento / leads_qualificados, 2) END) VIRTUAL,
  atualizacao   TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, data)
);

CREATE INDEX IF NOT EXISTS idx_ads_meta_campanhas_data ON ads_meta_campanhas (data);
CREATE INDEX IF NOT EXISTS idx_ads_meta_conjuntos_data ON ads_meta_conjuntos (data);
CREATE INDEX IF NOT EXISTS idx_ads_meta_anuncios_data ON ads_meta_anuncios (data);
CREATE INDEX IF NOT EXISTS idx_ads_google_campanhas_data ON ads_google_campanhas (data);
CREATE INDEX IF NOT EXISTS idx_ads_google_grupos_data ON ads_google_grupos (data);
CREATE INDEX IF NOT EXISTS idx_ads_google_termos_data ON ads_google_termos (data);
CREATE INDEX IF NOT EXISTS idx_ads_google_palavras_data ON ads_google_palavras (data);
