"""
Sincroniza métricas diárias do Google Ads (conta CWB Kids) para a planilha
SHEETS_ID_CWBKIDS_METRICAS.

Abas preenchidas:
  GOOGLE ADS - CAMPANHAS       (spend/impressões/cliques via Google Ads API +
  GOOGLE ADS - GRUPOS DE ANÚNCIOS  Page View/Add to Cart/Checkout/Compras/Receita via GA4)

Métricas de funil vêm do GA4 usando sessionGoogleAdsCampaignName (requer autotagging).
Grupos de anúncios ficam sem funil GA4 (GA4 não segmenta nesse nível).

Usa a biblioteca oficial google-ads (gRPC), pois o REST endpoint não está disponível.

Uso:
    python cwbkids_google_ads_sheet_sync.py                        # catch-up
    python cwbkids_google_ads_sheet_sync.py 2026-06-20             # data específica
    python cwbkids_google_ads_sheet_sync.py 2026-06-05 2026-06-20  # intervalo
"""
import json
import os
import sys
from datetime import date, timedelta

from google.ads.googleads.client import GoogleAdsClient as GadsClient
from google.ads.googleads.errors import GoogleAdsException

from cwbkids_commons import (
    GA4Client, SheetsClient, date_br_display, date_br_input, parse_env, safe_div,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
ID_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cwbkids_google_id_map.json")

TAB_CAMPANHAS = "GOOGLE ADS - CAMPANHAS"
TAB_GRUPOS    = "GOOGLE ADS - GRUPOS DE ANÚNCIOS"
TAB_TERMOS    = "GOOGLE ADS - TERMOS DE BUSCA"

TERMOS_HEADER = ["DATA", "TERMO", "CAMPANHA", "GRUPO DE ANÚNCIOS",
                 "IMPRESSÕES", "CLIQUES", "CTR", "CPC", "INVESTIMENTO"]


def ensure_header(sheets, sheet_id, tab, headers):
    # Verifica se a aba existe; se não, cria primeiro
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


# ── ID map ────────────────────────────────────────────────────────────────────

def load_id_map():
    if os.path.exists(ID_MAP_PATH):
        with open(ID_MAP_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"campaigns": {}, "adgroups": {}, "last_synced_date": None}


def save_id_map(id_map):
    with open(ID_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(id_map, f, ensure_ascii=False, indent=2)


def get_short_id(id_map, level, entity_id, parent_short_id):
    import re
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


# ── Google Ads gRPC client ────────────────────────────────────────────────────

def make_gads_client(env):
    return GadsClient.load_from_dict({
        "developer_token": env["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": env["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"].replace("-", ""),
        "use_proto_plus": True,
    })


def _pct(val):
    try:
        f = float(val)
        return f if 0.0 <= f <= 1.0 else 0.0
    except (TypeError, ValueError):
        return 0.0


# ── Sync de um dia ────────────────────────────────────────────────────────────

def sync_day(target_date, customer_id, gads, sheets, ga4, sheet_id, id_map):
    date_input   = date_br_input(target_date)
    date_display = date_br_display(target_date)
    date_str     = target_date.isoformat()
    print(f"--- {date_str} ---")

    ga_service = gads.get_service("GoogleAdsService")
    ga4_data   = ga4.fetch_by_campaign(date_str, "sessionGoogleAdsCampaignName")

    # ── CAMPANHAS ─────────────────────────────────────────────────────────────
    # Colunas (23): ID | DATA | CAMPANHA | NOME DE EXIBIÇÃO | OBJETIVO |
    # IMPRESSÕES | CLIQUES | PAGE VIEW | ADIÇÕES AO CARRINHO | CHECKOUT INICIADO |
    # COMPRAS | RECEITA | ROAS | CTR | CONNECT RATE |
    # PARCELA DE IMPRESSÕES | PARC IMP PERDIDA POR ORÇAMENTO |
    # PARC IMP PERDIDA POR CLASSIFICAÇÃO | TAXA DE CONVERSÃO | CPC | CPM | CPA | INVESTIMENTO
    # percent: [13,14,15,16,17,18]  currency: [11,19,20,21,22]

    camp_query = f"""
        SELECT campaign.id, campaign.name, campaign.advertising_channel_type,
               metrics.impressions, metrics.clicks, metrics.cost_micros,
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
            is_   = _pct(m.search_impression_share)
            is_b  = _pct(m.search_budget_lost_impression_share)
            is_r  = _pct(m.search_rank_lost_impression_share)
            g     = ga4_data.get(c.name, {})
            pv    = g.get("page_views", 0.0)
            atc   = g.get("add_to_cart", 0.0)
            bco   = g.get("begin_checkout", 0.0)
            comp  = g.get("purchases", 0.0)
            rev   = g.get("revenue", 0.0)
            sid   = get_short_id(id_map, "campaigns", c.id, None)
            if (sid, date_display) in existing:
                continue
            ch_type = str(c.advertising_channel_type.name) if c.advertising_channel_type else ""
            tipo = CHANNEL_LABELS.get(ch_type, ch_type)
            rows.append([
                sid, date_input, c.name, "", tipo,
                imp, cli, pv, atc, bco, comp, rev,
                safe_div(rev, spend),        # ROAS
                safe_div(cli, imp),          # CTR
                safe_div(pv, cli),           # CONNECT RATE
                is_, is_b, is_r,             # PARCELAS DE IMPRESSÃO
                safe_div(comp, pv),          # TAXA DE CONVERSÃO
                safe_div(spend, cli),        # CPC
                safe_div(spend, imp) * 1000, # CPM
                safe_div(spend, comp),       # CPA
                spend,
            ])
    except GoogleAdsException as ex:
        print(f"  CAMPANHAS erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_CAMPANHAS)
    sheets.append_and_format(sheet_id, gid, TAB_CAMPANHAS, rows,
                             percent_cols=[13, 14, 15, 16, 17, 18],
                             currency_cols=[11, 19, 20, 21, 22])
    print(f"  CAMPANHAS: {len(rows)} linha(s)")

    # ── GRUPOS DE ANÚNCIOS ────────────────────────────────────────────────────
    # Colunas (17): ID | DATA | CAMPANHA | GRUPOS DE ANÚNCIO | NOME DE EXIBIÇÃO |
    # IMPRESSÕES | CLIQUES | COMPRAS | RECEITA | CTR |
    # PARCELA DE IMPRESSÕES | PARC IMP PERDIDA POR ORÇAMENTO |
    # PARC IMP PERDIDA POR CLASSIFICAÇÃO | CPC | CPM | CPA | INVESTIMENTO
    # percent: [9]  currency: [13,14,16]

    grupo_query = f"""
        SELECT campaign.id, campaign.name, ad_group.id, ad_group.name,
               metrics.impressions, metrics.clicks, metrics.cost_micros
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
            c_sid = get_short_id(id_map, "campaigns", c.id, None)
            sid   = get_short_id(id_map, "adgroups", ag.id, c_sid)
            if (sid, date_display) in existing:
                continue
            rows.append([
                sid, date_input, c.name, ag.name, "",
                imp, cli,
                "", "",                      # COMPRAS / RECEITA (sem GA4 nesse nível)
                safe_div(cli, imp),          # CTR
                "", "", "",                  # PARCELAS (sem IS nesse nível)
                safe_div(spend, cli),        # CPC
                safe_div(spend, imp) * 1000, # CPM
                "",                          # CPA (sem compras)
                spend,                       # INVESTIMENTO
            ])
    except GoogleAdsException as ex:
        print(f"  GRUPOS erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_GRUPOS)
    sheets.append_and_format(sheet_id, gid, TAB_GRUPOS, rows,
                             percent_cols=[9],
                             currency_cols=[13, 14, 16])
    print(f"  GRUPOS:    {len(rows)} linha(s)")

    # ── TERMOS DE BUSCA ───────────────────────────────────────────────────────
    # Colunas: DATA | TERMO | CAMPANHA | GRUPO DE ANÚNCIOS |
    #          IMPRESSÕES | CLIQUES | CTR | CPC | INVESTIMENTO
    # percent: [6]  currency: [7, 8]

    termos_query = f"""
        SELECT search_term_view.search_term, campaign.name, ad_group.name,
               metrics.impressions, metrics.clicks, metrics.cost_micros
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
            if (date_input, termo) in existing_t:
                continue
            rows.append([
                date_input, termo, c.name, ag.name,
                imp, cli,
                safe_div(cli, imp),          # CTR
                safe_div(spend, cli),        # CPC
                spend,                       # INVESTIMENTO
            ])
    except GoogleAdsException as ex:
        print(f"  TERMOS erro: {ex}")
    gid = sheets.get_tab_gid(sheet_id, TAB_TERMOS)
    sheets.append_and_format(sheet_id, gid, TAB_TERMOS, rows,
                             percent_cols=[6],
                             currency_cols=[7, 8],
                             date_col=None)
    print(f"  TERMOS:    {len(rows)} linha(s)")


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

    env     = parse_env(ENV_PATH)
    id_map  = load_id_map()
    gads    = make_gads_client(env)
    sheets  = SheetsClient(env)
    ga4     = GA4Client(env)
    sheet_id   = env["SHEETS_ID_CWBKIDS_METRICAS"]
    customer_id = env["GOOGLE_ADS_CUSTOMER_ID_CWBKIDS"].replace("-", "")

    ensure_header(sheets, sheet_id, TAB_TERMOS, TERMOS_HEADER)

    d = start_date
    while d <= end_date:
        sync_day(d, customer_id, gads, sheets, ga4, sheet_id, id_map)
        d += timedelta(days=1)

    sheets.sort_tabs_by_date(sheet_id, [TAB_CAMPANHAS, TAB_GRUPOS])
    sheets.sort_tabs_by_date(sheet_id, [TAB_TERMOS], date_col_idx=0)
    id_map["last_synced_date"] = end_date.isoformat()
    save_id_map(id_map)


if __name__ == "__main__":
    main()
