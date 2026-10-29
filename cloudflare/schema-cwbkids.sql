CREATE TABLE IF NOT EXISTS marketplace (
  "data" TEXT NOT NULL,
  "marketplace" TEXT NOT NULL,
  "pedidos" REAL,
  "receita" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("data","marketplace")
);

CREATE INDEX IF NOT EXISTS idx_marketplace_data ON marketplace(data);

CREATE TABLE IF NOT EXISTS nuvemshop (
  "data" TEXT NOT NULL,
  "pedidos_totais_da_loja" REAL,
  "receita_total_da_loja" REAL,
  "sessoes" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("data")
);

CREATE INDEX IF NOT EXISTS idx_nuvemshop_data ON nuvemshop(data);

CREATE TABLE IF NOT EXISTS ads_meta_campanhas (
  "id" TEXT NOT NULL,
  "data" TEXT NOT NULL,
  "campanha" TEXT,
  "nome_exibicao" TEXT,
  "objetivo" TEXT,
  "impressoes" REAL,
  "cliques" REAL,
  "page_view" REAL,
  "add_to_cart" REAL,
  "initiate_checkout" REAL,
  "ctr_pct" REAL,
  "receita" REAL,
  "roas" REAL,
  "cpc" REAL,
  "connect_rate_pct" REAL,
  "taxa_conversao_pct" REAL,
  "cpc_alternativo_16" REAL,
  "cpm" REAL,
  "cpa" REAL,
  "investimento" REAL,
  "compras" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("id","data")
);

CREATE INDEX IF NOT EXISTS idx_ads_meta_campanhas_data ON ads_meta_campanhas(data);

CREATE TABLE IF NOT EXISTS ads_meta_conjuntos (
  "id" TEXT NOT NULL,
  "data" TEXT NOT NULL,
  "campanha" TEXT,
  "conjunto" TEXT,
  "nome_exibicao" TEXT,
  "nivel_publico" TEXT,
  "impressoes" REAL,
  "alcance" REAL,
  "cliques" REAL,
  "compras" REAL,
  "receita" REAL,
  "roas" REAL,
  "ctr_pct" REAL,
  "frequencia" REAL,
  "taxa_conversao_pct" REAL,
  "cpc" REAL,
  "cpm" REAL,
  "cpa" REAL,
  "investimento" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("id","data")
);

CREATE INDEX IF NOT EXISTS idx_ads_meta_conjuntos_data ON ads_meta_conjuntos(data);

CREATE TABLE IF NOT EXISTS ads_meta_anuncios (
  "id" TEXT NOT NULL,
  "data" TEXT NOT NULL,
  "campanha" TEXT,
  "conjunto" TEXT,
  "anuncio" TEXT,
  "nome_exibicao" TEXT,
  "impressoes" REAL,
  "alcance" REAL,
  "cliques" REAL,
  "reproducoes_3s" REAL,
  "compras" REAL,
  "ctr_pct" REAL,
  "roas" REAL,
  "cpc" REAL,
  "hook_rate_pct" REAL,
  "cpc_alternativo_15" REAL,
  "cpm" REAL,
  "cpa" REAL,
  "investimento" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("id","data")
);

CREATE INDEX IF NOT EXISTS idx_ads_meta_anuncios_data ON ads_meta_anuncios(data);

CREATE TABLE IF NOT EXISTS ads_google_campanhas (
  "id" TEXT NOT NULL,
  "data" TEXT NOT NULL,
  "campanha" TEXT,
  "nome_exibicao" TEXT,
  "objetivo" TEXT,
  "impressoes" REAL,
  "cliques" REAL,
  "page_view" REAL,
  "adicoes_ao_carrinho" REAL,
  "checkout_iniciado" REAL,
  "compras" REAL,
  "receita" REAL,
  "roas" REAL,
  "ctr_pct" REAL,
  "connect_rate_pct" REAL,
  "parcela_impressoes_pct" REAL,
  "parc_perdida_orcamento_pct" REAL,
  "parc_perdida_classif_pct" REAL,
  "taxa_conversao_pct" REAL,
  "cpc" REAL,
  "cpm" REAL,
  "cpa" REAL,
  "investimento" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("id","data")
);

CREATE INDEX IF NOT EXISTS idx_ads_google_campanhas_data ON ads_google_campanhas(data);

CREATE TABLE IF NOT EXISTS ads_google_grupos (
  "id" TEXT NOT NULL,
  "data" TEXT NOT NULL,
  "campanha" TEXT,
  "grupo" TEXT,
  "nome_exibicao" TEXT,
  "impressoes" REAL,
  "cliques" REAL,
  "compras" REAL,
  "receita" REAL,
  "ctr_pct" REAL,
  "nao_utilizado" REAL,
  "nao_utilizado_alternativo_11" REAL,
  "nao_utilizado_alternativo_12" REAL,
  "cpc" REAL,
  "cpm" REAL,
  "cpa" REAL,
  "investimento" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("id","data")
);

CREATE INDEX IF NOT EXISTS idx_ads_google_grupos_data ON ads_google_grupos(data);

CREATE TABLE IF NOT EXISTS ads_google_termos (
  "data" TEXT NOT NULL,
  "termo" TEXT NOT NULL,
  "campanha" TEXT NOT NULL,
  "grupo" TEXT NOT NULL,
  "impressoes" REAL,
  "cliques" REAL,
  "ctr_pct" REAL,
  "cpc" REAL,
  "investimento" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("data","termo","campanha","grupo")
);

CREATE INDEX IF NOT EXISTS idx_ads_google_termos_data ON ads_google_termos(data);
