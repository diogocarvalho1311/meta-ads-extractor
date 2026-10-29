export const SCHEMA = {
  "meta-campanhas": {
    "table": "ads_meta_campanhas",
    "headers": [
      "ID",
      "DATA",
      "CAMPANHA",
      "NOME DE EXIBIÇÃO NO DASHBOARD",
      "OBJETIVO",
      "DESTINO LINK?",
      "IMPRESSÕES",
      "CLIQUES NO LINK",
      "PAGE VIEW",
      "LEADS",
      "LEADS QUALIFICADOS",
      "LEADS FECHADOS",
      "CTR (LINK)",
      "CONNECT RATE",
      "TAXA DE CONVERSÃO",
      "CPC (LINK)",
      "CPM",
      "CPA",
      "CPLQ",
      "INVESTIMENTO"
    ],
    "fields": [
      "id",
      "data",
      "campanha",
      "nome_exibicao",
      "objetivo",
      "destino_link",
      "impressoes",
      "cliques",
      "page_view",
      "leads",
      "leads_qualificados",
      "leads_fechados",
      "ctr_pct",
      "connect_rate_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq",
      "investimento"
    ],
    "keys": [
      "id",
      "data"
    ],
    "text": [
      "id",
      "campanha",
      "nome_exibicao",
      "objetivo"
    ],
    "percent": [
      "ctr_pct",
      "connect_rate_pct",
      "taxa_conversao_pct"
    ],
    "generated": [
      "ctr_pct",
      "connect_rate_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq"
    ],
    "gid": 864690883
  },
  "meta-conjuntos": {
    "table": "ads_meta_conjuntos",
    "headers": [
      "ID",
      "DATA",
      "CAMPANHA",
      "CONJUNTO DE ANÚNCIO",
      "NOME DE EXIBIÇÃO NO DASHBOARD",
      "NÍVEL DE PÚBLICO",
      "IMPRESSÕES",
      "ALCANCE",
      "CLIQUES NO LINK",
      "PAGE VIEW",
      "LEADS",
      "LEADS QUALIFICADOS",
      "LEADS FECHADOS",
      "CTR (LINK)",
      "FREQUÊNCIA",
      "CONNECT RATE",
      "TAXA DE CONVERSÃO",
      "CPC (LINK)",
      "CPM",
      "CPA",
      "CPLQ",
      "INVESTIMENTO"
    ],
    "fields": [
      "id",
      "data",
      "campanha",
      "conjunto",
      "nome_exibicao",
      "nivel_publico",
      "impressoes",
      "alcance",
      "cliques",
      "page_view",
      "leads",
      "leads_qualificados",
      "leads_fechados",
      "ctr_pct",
      "frequencia",
      "connect_rate_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq",
      "investimento"
    ],
    "keys": [
      "id",
      "data"
    ],
    "text": [
      "id",
      "campanha",
      "conjunto",
      "nome_exibicao",
      "nivel_publico"
    ],
    "percent": [
      "ctr_pct",
      "connect_rate_pct",
      "taxa_conversao_pct"
    ],
    "generated": [
      "ctr_pct",
      "frequencia",
      "connect_rate_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq"
    ],
    "gid": 713243316
  },
  "meta-anuncios": {
    "table": "ads_meta_anuncios",
    "headers": [
      "ID",
      "DATA",
      "CAMPANHA",
      "CONJUNTO DE ANÚNCIO",
      "ANÚNCIO",
      "NOME DE EXIBIÇÃO NO DASHBOARD",
      "IMPRESSÕES",
      "ALCANCE",
      "CLIQUES NO LINK",
      "REPRODUÇÕES DE 3 SEG",
      "LEADS",
      "LEADS QUALIFICADOS",
      "LEADS FECHADOS",
      "CTR (LINK)",
      "HOOK RATE",
      "CPC (LINK)",
      "CPM",
      "CPA",
      "CPLQ",
      "INVESTIMENTO"
    ],
    "fields": [
      "id",
      "data",
      "campanha",
      "conjunto",
      "anuncio",
      "nome_exibicao",
      "impressoes",
      "alcance",
      "cliques",
      "reproducoes_3s",
      "leads",
      "leads_qualificados",
      "leads_fechados",
      "ctr_pct",
      "hook_rate_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq",
      "investimento"
    ],
    "keys": [
      "id",
      "data"
    ],
    "text": [
      "id",
      "campanha",
      "conjunto",
      "anuncio",
      "nome_exibicao"
    ],
    "percent": [
      "ctr_pct",
      "hook_rate_pct"
    ],
    "generated": [
      "ctr_pct",
      "hook_rate_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq"
    ],
    "gid": 1150614650
  },
  "google-campanhas": {
    "table": "ads_google_campanhas",
    "headers": [
      "ID",
      "DATA",
      "CAMPANHA",
      "NOME DE EXIBIÇÃO NO DASHBOARD",
      "OBJETIVO",
      "IMPRESSÕES",
      "CLIQUES",
      "PAGE VIEW",
      "LEADS",
      "LEADS QUALIFICADOS",
      "LEADS FECHADOS",
      "CTR",
      "CONNECT RATE",
      "PARCELA DE IMPRESSÕES",
      "PARC IMP PERDIDA POR ORÇAMENTO",
      "PARC IMP PERDIDA POR CLASSIFICAÇÃO",
      "TAXA DE CONVERSÃO",
      "CPC",
      "CPM",
      "CPA",
      "CPLQ",
      "INVESTIMENTO"
    ],
    "fields": [
      "id",
      "data",
      "campanha",
      "nome_exibicao",
      "objetivo",
      "impressoes",
      "cliques",
      "page_view",
      "leads",
      "leads_qualificados",
      "leads_fechados",
      "ctr_pct",
      "connect_rate_pct",
      "parcela_impressoes_pct",
      "parc_perdida_orcamento_pct",
      "parc_perdida_classif_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq",
      "investimento"
    ],
    "keys": [
      "id",
      "data"
    ],
    "text": [
      "id",
      "campanha",
      "nome_exibicao",
      "objetivo"
    ],
    "percent": [
      "ctr_pct",
      "connect_rate_pct",
      "parcela_impressoes_pct",
      "parc_perdida_orcamento_pct",
      "parc_perdida_classif_pct",
      "taxa_conversao_pct"
    ],
    "generated": [
      "ctr_pct",
      "connect_rate_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq"
    ],
    "gid": 899444652
  },
  "google-grupos": {
    "table": "ads_google_grupos",
    "headers": [
      "ID",
      "DATA",
      "CAMPANHA",
      "GRUPOS DE ANÚNCIO",
      "NOME DE EXIBIÇÃO NO DASHBOARD",
      "IMPRESSÕES",
      "CLIQUES",
      "PAGE VIEW",
      "LEADS",
      "LEADS QUALIFICADOS",
      "LEADS FECHADOS",
      "NÍVEL DE QUALIDADE",
      "ÍNDICE DE EXP DO USUÁRIO",
      "ÍNDICE DE RELEV DO ANÚNCIO",
      "ÍNDICE DE CTR ESPERADO",
      "CTR",
      "CONNECT RATE",
      "PARCELA DE IMPRESSÕES",
      "PARC IMP PERDIDA POR ORÇAMENTO",
      "PARC IMP PERDIDA POR CLASSIFICAÇÃO",
      "TAXA DE CONVERSÃO",
      "CPC",
      "CPM",
      "CPA",
      "CPLQ",
      "INVESTIMENTO"
    ],
    "fields": [
      "id",
      "data",
      "campanha",
      "grupo",
      "nome_exibicao",
      "impressoes",
      "cliques",
      "page_view",
      "leads",
      "leads_qualificados",
      "leads_fechados",
      "nivel_qualidade",
      "indice_exp_usuario",
      "indice_relev_anuncio",
      "indice_ctr_esperado",
      "ctr_pct",
      "connect_rate_pct",
      "parcela_impressoes_pct",
      "parc_perdida_orcamento_pct",
      "parc_perdida_classif_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq",
      "investimento"
    ],
    "keys": [
      "id",
      "data"
    ],
    "text": [
      "id",
      "campanha",
      "grupo",
      "nome_exibicao",
      "indice_exp_usuario",
      "indice_relev_anuncio",
      "indice_ctr_esperado"
    ],
    "percent": [
      "ctr_pct",
      "connect_rate_pct",
      "parcela_impressoes_pct",
      "parc_perdida_orcamento_pct",
      "parc_perdida_classif_pct",
      "taxa_conversao_pct"
    ],
    "generated": [
      "ctr_pct",
      "connect_rate_pct",
      "taxa_conversao_pct",
      "cpc",
      "cpm",
      "cpa",
      "cplq"
    ],
    "gid": 1653129930
  },
  "google-termos": {
    "table": "ads_google_termos",
    "headers": [
      "DATA",
      "TERMO DE PESQUISA",
      "CAMPANHA",
      "GRUPO DE ANÚNCIO",
      "IMPRESSÕES",
      "CLIQUES",
      "LEADS",
      "CTR",
      "CPC",
      "CPA",
      "INVESTIMENTO"
    ],
    "fields": [
      "data",
      "termo",
      "campanha",
      "grupo",
      "impressoes",
      "cliques",
      "leads",
      "ctr_pct",
      "cpc",
      "cpa",
      "investimento"
    ],
    "keys": [
      "data",
      "termo",
      "campanha",
      "grupo"
    ],
    "text": [
      "termo",
      "campanha",
      "grupo"
    ],
    "percent": [
      "ctr_pct"
    ],
    "generated": [
      "ctr_pct",
      "cpc",
      "cpa"
    ],
    "gid": 211056975
  },
  "google-palavras": {
    "table": "ads_google_palavras",
    "headers": [
      "ID",
      "DATA",
      "CAMPANHA",
      "GRUPO DE ANÚNCIO",
      "PALAVRA-CHAVE",
      "TIPO DE CORRESPONDÊNCIA",
      "IMPRESSÕES",
      "CLIQUES",
      "LEADS",
      "LEADS QUALIFICADOS",
      "LEADS FECHADOS",
      "CTR",
      "CPC",
      "CPA",
      "CPLQ",
      "NÍVEL DE QUALIDADE",
      "INVESTIMENTO"
    ],
    "fields": [
      "id",
      "data",
      "campanha",
      "grupo",
      "palavra_chave",
      "tipo_correspondencia",
      "impressoes",
      "cliques",
      "leads",
      "leads_qualificados",
      "leads_fechados",
      "ctr_pct",
      "cpc",
      "cpa",
      "cplq",
      "nivel_qualidade",
      "investimento"
    ],
    "keys": [
      "id",
      "data"
    ],
    "text": [
      "id",
      "campanha",
      "grupo",
      "palavra_chave",
      "tipo_correspondencia"
    ],
    "percent": [
      "ctr_pct"
    ],
    "generated": [
      "ctr_pct",
      "cpc",
      "cpa",
      "cplq"
    ],
    "gid": 1159152013
  },
  "ga4-paginas": {
    "table": "ga4_paginas",
    "headers": [
      "DATA",
      "PÁGINA",
      "SESSÕES",
      "USUÁRIOS",
      "NOVOS USUÁRIOS",
      "VISUALIZAÇÕES",
      "SESSÕES ENGAJADAS",
      "TAXA DE ENGAJAMENTO",
      "TEMPO MÉD. ENGAJAMENTO (s)",
      "TAXA DE REJEIÇÃO"
    ],
    "fields": [
      "data",
      "pagina",
      "sessoes",
      "usuarios",
      "novos_usuarios",
      "visualizacoes",
      "sessoes_engajadas",
      "taxa_de_engajamento",
      "tempo_medio_engajamento_s",
      "taxa_de_rejeicao"
    ],
    "keys": [
      "data",
      "pagina"
    ],
    "text": [
      "pagina"
    ],
    "percent": [
      "taxa_de_engajamento",
      "taxa_de_rejeicao"
    ],
    "generated": [],
    "gid": 1315628149
  },
  "ga4-quiz-lp": {
    "table": "ga4_quiz_lp",
    "headers": [
      "DATA",
      "NOME",
      "WHATSAPP",
      "EMPRESA",
      "FATURAMENTO",
      "DESAFIO",
      "OBRIGADO"
    ],
    "fields": [
      "data",
      "nome",
      "whatsapp",
      "empresa",
      "faturamento",
      "desafio",
      "obrigado"
    ],
    "keys": [
      "data"
    ],
    "text": [],
    "percent": [],
    "generated": [],
    "gid": 1509772666
  },
  "ga4-quiz-typeform": {
    "table": "ga4_quiz_typeform",
    "headers": [
      "DATA",
      "NOME",
      "WHATSAPP",
      "EMPRESA",
      "DOR",
      "QUEM_CUIDA",
      "FATURAMENTO",
      "ORCAMENTO",
      "LEAD",
      "MEIO_LEAD",
      "NAO_LEAD"
    ],
    "fields": [
      "data",
      "nome",
      "whatsapp",
      "empresa",
      "dor",
      "quem_cuida",
      "faturamento",
      "orcamento",
      "lead",
      "meio_lead",
      "nao_lead"
    ],
    "keys": [
      "data"
    ],
    "text": [],
    "percent": [],
    "generated": [],
    "gid": 1352440719
  }
};
