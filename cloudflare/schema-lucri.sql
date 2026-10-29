CREATE TABLE IF NOT EXISTS crm_leads (
  "notion_id" TEXT NOT NULL,
  "data" TEXT,
  "nome" TEXT,
  "empresa" TEXT,
  "telefone" TEXT,
  "dor" TEXT,
  "faturamento" TEXT,
  "orcamento" TEXT,
  "quem_cuida" TEXT,
  "qualidade_do_lead" TEXT,
  "status" TEXT,
  "utm_campaign" TEXT,
  "utm_source" TEXT,
  "utm_medium" TEXT,
  "utm_content" TEXT,
  "utm_term" TEXT,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("notion_id")
);

CREATE INDEX IF NOT EXISTS idx_crm_leads_data ON crm_leads(data);

CREATE TABLE IF NOT EXISTS ga4_paginas (
  "data" TEXT NOT NULL,
  "pagina" TEXT NOT NULL,
  "sessoes" REAL,
  "usuarios" REAL,
  "novos_usuarios" REAL,
  "visualizacoes" REAL,
  "sessoes_engajadas" REAL,
  "taxa_de_engajamento" REAL,
  "tempo_medio_engajamento_s" REAL,
  "taxa_de_rejeicao" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("data","pagina")
);

CREATE INDEX IF NOT EXISTS idx_ga4_paginas_data ON ga4_paginas(data);

CREATE TABLE IF NOT EXISTS ga4_quiz_lp (
  "data" TEXT NOT NULL,
  "nome" REAL,
  "whatsapp" REAL,
  "empresa" REAL,
  "faturamento" REAL,
  "desafio" REAL,
  "obrigado" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("data")
);

CREATE INDEX IF NOT EXISTS idx_ga4_quiz_lp_data ON ga4_quiz_lp(data);

CREATE TABLE IF NOT EXISTS ga4_quiz_typeform (
  "data" TEXT NOT NULL,
  "nome" REAL,
  "whatsapp" REAL,
  "empresa" REAL,
  "dor" REAL,
  "quem_cuida" REAL,
  "faturamento" REAL,
  "orcamento" REAL,
  "lead" REAL,
  "meio_lead" REAL,
  "nao_lead" REAL,
  atualizacao TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY ("data")
);

CREATE INDEX IF NOT EXISTS idx_ga4_quiz_typeform_data ON ga4_quiz_typeform(data);
