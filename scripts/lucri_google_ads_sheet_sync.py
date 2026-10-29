"""
Sincroniza métricas diárias do Google Ads (conta Lucri Finanças) para a planilha.

Abas preenchidas:
  GOOGLE ADS - CAMPANHAS         (19 colunas)
  GOOGLE ADS - GRUPOS DE ANÚNCIO (23 colunas)
  GOOGLE ADS - TERMOS DE BUSCA   (11 colunas)
  GOOGLE ADS - PALAVRAS-CHAVE    (14 colunas)

Diferenças em relação à CWB Kids:
  - Sem GA4 (Lucri não tem propriedade GA4) — LEADS vem de metrics.conversions
    (conversões configuradas na própria conta do Google Ads), não do funil de e-commerce
  - Campanhas de LEADS, não de compras/receita
  - Grupos têm colunas de qualidade — deixadas em branco (nível de keyword, não de grupo)

Uso:
    python lucri_google_ads_sheet_sync.py                        # catch-up
    python lucri_google_ads_sheet_sync.py 2026-07-20             # data específica
    python lucri_google_ads_sheet_sync.py 2026-07-01 2026-07-20  # intervalo
"""
import json
import os
import re
import sys
from datetime import date, timedelta

from google.ads.googleads.client import GoogleAdsClient as GadsClient
from google.ads.googleads.errors import GoogleAdsException

from cwbkids_commons import (
    SheetsClient, date_br_display, date_br_input, parse_env, safe_div,
)

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH    = os.path.join(BASE_DIR, ".env")
ID_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lucri_google_id_map.json")

TAB_CAMPANHAS = "GOOGLE ADS - CAMPANHAS"
TAB_GRUPOS    = "GOOGLE ADS - GRUPOS DE ANÚNCIO"
TAB_TERMOS    = "GOOGLE ADS - TERMOS DE BUSCA"
TAB_PALAVRAS  = "GOOGLE ADS - PALAVRAS-CHAVE"

TERMOS_HEADER = ["DATA", "TERMO DE PESQUISA", "CAMPANHA", "GRUPO DE ANÚNCIO",
                 "IMPRESSÕES", "CLIQUES", "LEADS", "CTR", "CPC", "CPA", "INVESTIMENTO"]
PALAVRAS_HEADER = ["ID", "DATA", "CAMPANHA", "GRUPO DE ANÚNCIO", "PALAVRA-CHAVE",
                    "TIPO DE CORRESPONDÊNCIA", "IMPRESSÕES", "CLIQUES", "LEADS",
                    "CTR", "CPC", "CPA", "NÍVEL DE QUALIDADE", "INVESTIMENTO"]

MATCH_TYPE_LABELS = {
    "EXACT": "EXATA", "PHRASE": "FRASE", "BROAD": "AMPLA",
    "UNKNOWN": "", "UNSPECIFIED": "",
}

def format_keyword(text, match_type):
    if match_type == "EXACT":
        return f"[{text}]"
    if match_type == "PHRASE":
        return f'"{text}"'
    return text


def ensure_header(sheets, sheet_id, tab, headers):
    meta = sheets.get(sheet_id)
    tab_titles = [s["properties"]["title"] for s in meta["sheets"]]
    if tab not in tab_titles:
        sheets.batch_update(sheet_id, [{"addSheet": {"properties": {"title": tab}}}])
    result = sheets.values_get(sheet_id, f"{tab}!A1:A1")
    if not result.get("values"):
        sheets.values_append(sheet_id, f"{tab}!A1", [headers])


CHANNEL_LABELS = {
    "SEARCH": "PESQUISA", "DISPLAY": "DISPLAY", "SHOPPING": "SHOPPING",
    "VIDEO": "VÍDEO", "PERFORMANCE_MAX": "PMAX", "MULTI_CHANNEL": "MULTI-CANAL",
    "UNSPECIFIED": "", "UNKNOWN": "",
}


def load_id_map():
    if os.path.exists(ID_MAP_PATH):
        with open(ID_MAP_PATH, encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("keywords", {})
            return data
    return {"campaigns": {}, "adgroups": {}, "keywords": {}, "last_synced_date": None}


def save_id_map(id_map):
    with open(ID_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(id_map, f, ensure_ascii=False, indent=2)


def get_short_id(id_map, level, entity_id, parent_short_id):
    bucket = id_map[level]
    key = str(entity_id)
    if key in bucket:
        return bucket[key]
    prefix = f"{parent_short_id}." if parent_short_id else "g"
    nums = [
        int(v[len(prefix):]) for v in bucket.values()
        if parent_short_id and v.startswith(prefix) and v[len(prefix):].isdigit()
    ] if parent_short_id else [
        int(v[1:]) for v in bucket.values() if re.fullmatch(r"g\d+", v)
    ]
    n = max(nums, default=0) + 1
    short_id = f"{prefix}{n}" if parent_short_id else f"g{n}"
    bucket[key] = short_id
    return short_id


def make_gads_client(env):
    return GadsClient.load_from_dict({
        "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id":       env["GOOGLE_ADS_CLIENT_ID"],
        "client_secret":   env["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token":   env["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"].replace("-", ""),
        "use_proto_plus":  True,
    })


def _pct(val):
    try:
        f = float(val)
        return f if 0.0 <= f <= 1.0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def sync_day(target_date, customer_id, gads, sheets, sheet_id, id_map):
    date_input   = date_br_input(target_date)
    date_display = date_br_display(target_date)
    date_str     = target_date.isoformat()
    print(f"--- {date_str} ---")

    ga_service = gads.get_service("GoogleAdsService")

    # ── CAMPANHAS (22 colunas) ─────────────────────────────────────────────────
    # ID(0) DATA(1) CAMPANHA(2) NOME_DISPLAY(3) OBJETIVO(4)
    # IMP(5) CLI(6) PAGE_VIEW(7) LEADS(8) LEADS_QUALIFICADOS(9) LEADS_FECHADOS(10)
    # CTR(11) CONNECT_RATE(12) PARC_IMP(13) PARC_ORC(14) PARC_CLASS(15) TAXA_CONV(16)
    # CPC(17) CPM(18) CPA(19) CPLQ(20) INVEST(21)
    # percent_cols=[11,12,13,14,15,16]  currency_cols=[17,18,19,21]
    # LEADS_QUALIFICADOS, LEADS_FECHADOS e CPLQ são preenchidos manualmente
    # depois, por lucri_leads_qualificados_google_sync.py — aqui só entra o placeholder.

    camp_query = f"""
        SELECT campaign.id, campaign.name, campaign.advertising_channel_type,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions,
               metrics.search_impression_share,
               metrics.search_budget_lost_impression_share,
               metrics.search_rank_lost_impression_share
        FROM campaign
        WHERE segments.date = '{date_str}'
          AND metrics.impressions > 0
    """
    existing = sheets.existing_keys(sheet_id, TAB_CAMPANHAS)
    rows = []
    try:
        for row in ga_service.search(customer_id=customer_id, query=camp_query):
            c = row.campaign
            m = row.metrics
            imp   = float(m.impressions)
            cli   = float(m.clicks)
            spend = float(m.cost_micros) / 1_000_000
            leads = float(m.conversions)  # conversões configuradas na conta do Google Ads (não depende de GA4)
            is_   = _pct(m.search_impression_share)
            is_b  = _pct(m.search_budget_lost_impression_share)
            is_r  = _pct(m.search_rank_lost_impression_share)
            sid   = get_short_id(id_map, "campaigns", c.id, None)
            if (sid, date_display) in existing:
                continue
            ch_type = str(c.advertising_channel_type.name) if c.advertising_channel_type else ""
            tipo = CHANNEL_LABELS.get(ch_type, ch_type)
            rows.append([
                sid, date_input, c.name, "", tipo,
                imp, cli, 0, leads,            # PAGE_VIEW (sem GA4) e LEADS
                0,                              # LEADS_QUALIFICADOS (manual)
                0,                              # LEADS_FECHADOS (manual)
                safe_div(cli, imp),            # CTR
                0.0,                           # CONNECT_RATE
                is_, is_b, is_r,              # PARCELAS
                safe_div(leads, cli),          # TAXA_CONV (cliques -> lead, sem etapa de page view)
                safe_div(spend, cli),          # CPC
                safe_div(spend, imp) * 1000,   # CPM
                safe_div(spend, leads),        # CPA
                "",                             # CPLQ
                spend,
            ])
    except GoogleAdsException as ex:
        print(f"  CAMPANHAS erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_CAMPANHAS)
    sheets.append_and_format(sheet_id, gid, TAB_CAMPANHAS, rows,
                             percent_cols=[11, 12, 13, 14, 15, 16],
                             currency_cols=[17, 18, 19, 21])
    print(f"  CAMPANHAS: {len(rows)} linha(s)")

    # ── GRUPOS DE ANÚNCIO (26 colunas) ────────────────────────────────────────
    # ID(0) DATA(1) CAMP(2) GRUPO(3) NOME_DISPLAY(4)
    # IMP(5) CLI(6) PAGE_VIEW(7) LEADS(8) LEADS_QUALIFICADOS(9) LEADS_FECHADOS(10)
    # QUALIDADE(11) EXP_USU(12) RELEV_AD(13) CTR_ESP(14)
    # CTR(15) CONNECT_RATE(16) PARC_IMP(17) PARC_ORC(18) PARC_CLASS(19) TAXA_CONV(20)
    # CPC(21) CPM(22) CPA(23) CPLQ(24) INVEST(25)
    # percent_cols=[15,16,17,18,19,20]  currency_cols=[21,22,23,25]
    # LEADS_QUALIFICADOS, LEADS_FECHADOS e CPLQ são preenchidos manualmente
    # depois, por lucri_leads_qualificados_google_sync.py — aqui só entra o placeholder.

    grupo_query = f"""
        SELECT campaign.id, campaign.name, ad_group.id, ad_group.name,
               metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
        FROM ad_group
        WHERE segments.date = '{date_str}'
          AND metrics.impressions > 0
    """
    existing = sheets.existing_keys(sheet_id, TAB_GRUPOS)
    rows = []
    try:
        for row in ga_service.search(customer_id=customer_id, query=grupo_query):
            c  = row.campaign
            ag = row.ad_group
            m  = row.metrics
            imp   = float(m.impressions)
            cli   = float(m.clicks)
            spend = float(m.cost_micros) / 1_000_000
            leads = float(m.conversions)
            c_sid = get_short_id(id_map, "campaigns", c.id, None)
            sid   = get_short_id(id_map, "adgroups", ag.id, c_sid)
            if (sid, date_display) in existing:
                continue
            rows.append([
                sid, date_input, c.name, ag.name, "",
                imp, cli, 0, leads,            # PAGE_VIEW (sem GA4) e LEADS
                0,                              # LEADS_QUALIFICADOS (manual)
                0,                              # LEADS_FECHADOS (manual)
                "", "", "", "",               # qualidade (nível keyword, não grupo)
                safe_div(cli, imp),            # CTR
                0.0,                           # CONNECT_RATE
                "", "", "",                   # PARCELAS (sem IS em grupos)
                safe_div(leads, cli),          # TAXA_CONV
                safe_div(spend, cli),          # CPC
                safe_div(spend, imp) * 1000,   # CPM
                safe_div(spend, leads),        # CPA
                "",                             # CPLQ
                spend,
            ])
    except GoogleAdsException as ex:
        print(f"  GRUPOS erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_GRUPOS)
    sheets.append_and_format(sheet_id, gid, TAB_GRUPOS, rows,
                             percent_cols=[15, 16, 17, 18, 19, 20],
                             currency_cols=[21, 22, 23, 25])
    print(f"  GRUPOS:    {len(rows)} linha(s)")

    # ── TERMOS DE BUSCA (11 colunas) ──────────────────────────────────────────
    # DATA(0) TERMO(1) CAMPANHA(2) GRUPO(3) IMP(4) CLI(5) LEADS(6) CTR(7) CPC(8) CPA(9) INVEST(10)
    # percent_cols=[7]  currency_cols=[8,9,10]  date_col=None (dedup por DATA+TERMO em texto)

    termos_query = f"""
        SELECT search_term_view.search_term, campaign.name, ad_group.name,
               metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
        FROM search_term_view
        WHERE segments.date = '{date_str}'
          AND metrics.impressions > 0
    """
    existing_t = sheets.existing_keys(sheet_id, TAB_TERMOS)
    rows = []
    try:
        for row in ga_service.search(customer_id=customer_id, query=termos_query):
            st  = row.search_term_view
            c   = row.campaign
            ag  = row.ad_group
            m   = row.metrics
            termo = st.search_term
            imp   = float(m.impressions)
            cli   = float(m.clicks)
            spend = float(m.cost_micros) / 1_000_000
            leads = float(m.conversions)
            if (date_input, termo) in existing_t:
                continue
            rows.append([
                date_input, termo, c.name, ag.name,
                imp, cli, leads,
                safe_div(cli, imp),      # CTR
                safe_div(spend, cli),    # CPC
                safe_div(spend, leads),  # CPA
                spend,                   # INVESTIMENTO
            ])
    except GoogleAdsException as ex:
        print(f"  TERMOS erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_TERMOS)
    sheets.append_and_format(sheet_id, gid, TAB_TERMOS, rows,
                             percent_cols=[7],
                             currency_cols=[8, 9, 10],
                             date_col=None)
    print(f"  TERMOS:    {len(rows)} linha(s)")

    # ── PALAVRAS-CHAVE (17 colunas) ───────────────────────────────────────────
    # ID(0) DATA(1) CAMPANHA(2) GRUPO(3) PALAVRA(4) TIPO(5)
    # IMP(6) CLI(7) LEADS(8) LEADS_QUALIFICADOS(9) LEADS_FECHADOS(10)
    # CTR(11) CPC(12) CPA(13) CPLQ(14) QUALIDADE(15) INVEST(16)
    # percent_cols=[11]  currency_cols=[12,13,14,16]
    # LEADS_QUALIFICADOS, LEADS_FECHADOS e CPLQ são preenchidos manualmente
    # depois, por lucri_leads_qualificados_google_sync.py — aqui só entra o placeholder.

    palavras_query = f"""
        SELECT campaign.id, campaign.name, ad_group.id, ad_group.name,
               ad_group_criterion.criterion_id, ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type,
               ad_group_criterion.quality_info.quality_score,
               metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
        FROM keyword_view
        WHERE segments.date = '{date_str}'
          AND metrics.impressions > 0
    """
    existing_p = sheets.existing_keys(sheet_id, TAB_PALAVRAS)
    rows = []
    try:
        for row in ga_service.search(customer_id=customer_id, query=palavras_query):
            c   = row.campaign
            ag  = row.ad_group
            crit = row.ad_group_criterion
            m   = row.metrics
            imp   = float(m.impressions)
            cli   = float(m.clicks)
            spend = float(m.cost_micros) / 1_000_000
            leads = float(m.conversions)
            match_type = str(crit.keyword.match_type.name) if crit.keyword.match_type else ""
            quality = crit.quality_info.quality_score
            c_sid  = get_short_id(id_map, "campaigns", c.id, None)
            ag_sid = get_short_id(id_map, "adgroups", ag.id, c_sid)
            sid    = get_short_id(id_map, "keywords", crit.criterion_id, ag_sid)
            if (sid, date_display) in existing_p:
                continue
            rows.append([
                sid, date_input, c.name, ag.name, format_keyword(crit.keyword.text, match_type),
                MATCH_TYPE_LABELS.get(match_type, match_type),
                imp, cli, leads,
                0,                        # LEADS_QUALIFICADOS (manual)
                0,                        # LEADS_FECHADOS (manual)
                safe_div(cli, imp),      # CTR
                safe_div(spend, cli),    # CPC
                safe_div(spend, leads),  # CPA
                "",                       # CPLQ
                quality if quality else "",  # NÍVEL DE QUALIDADE (0 = não calculado ainda)
                spend,
            ])
    except GoogleAdsException as ex:
        print(f"  PALAVRAS-CHAVE erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_PALAVRAS)
    sheets.append_and_format(sheet_id, gid, TAB_PALAVRAS, rows,
                             percent_cols=[11],
                             currency_cols=[12, 13, 14, 16])
    print(f"  PALAVRAS-CHAVE: {len(rows)} linha(s)")


def main():
    yesterday = date.today() - timedelta(days=1)
    if len(sys.argv) == 3:
        start_date, end_date = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
    elif len(sys.argv) == 2:
        start_date = end_date = date.fromisoformat(sys.argv[1])
    else:
        id_map_peek = load_id_map()
        last = id_map_peek.get("last_synced_date")
        start_date = date.fromisoformat(last) + timedelta(days=1) if last else yesterday
        end_date = yesterday

    if start_date > end_date:
        print(f"Nada a sincronizar (último dia: {start_date - timedelta(days=1)}).")
        return

    env         = parse_env(ENV_PATH)
    id_map      = load_id_map()
    gads        = make_gads_client(env)
    sheets      = SheetsClient(env)
    sheet_id    = env["SHEETS_ID_LUCRI_METRICAS"]
    customer_id = env["GOOGLE_ADS_CUSTOMER_ID_LUCRI"].replace("-", "")

    ensure_header(sheets, sheet_id, TAB_TERMOS, TERMOS_HEADER)
    ensure_header(sheets, sheet_id, TAB_PALAVRAS, PALAVRAS_HEADER)

    d = start_date
    while d <= end_date:
        sync_day(d, customer_id, gads, sheets, sheet_id, id_map)
        d += timedelta(days=1)

    sheets.sort_tabs_by_date(sheet_id, [TAB_CAMPANHAS, TAB_GRUPOS, TAB_PALAVRAS])
    sheets.sort_tabs_by_date(sheet_id, [TAB_TERMOS], date_col_idx=0)
    id_map["last_synced_date"] = end_date.isoformat()
    save_id_map(id_map)


if __name__ == "__main__":
    main()
