"""
Puxa métricas de comportamento do GA4 da Lucri e grava na planilha de métricas.

Páginas rastreadas:
  lp               → lp.lucrifinancas.com.br/
  lp2              → lp.lucrifinancas.com.br/2
  typeform         → type.lucrifinancas.com.br/
  lp_obrigado      → lp.lucrifinancas.com.br/obrigado
  site             → lucrifinancas.com.br/
  site_servicos    → lucrifinancas.com.br/servicos
  site_sobre       → lucrifinancas.com.br/sobre
  site_contato     → lucrifinancas.com.br/contato
  site_ferramentas → lucrifinancas.com.br/ferramentas

Colunas gravadas por dia/página:
  DATA | PÁGINA | SESSÕES | USUÁRIOS | NOVOS USUÁRIOS | VISUALIZAÇÕES |
  SESSÕES ENGAJADAS | TAXA DE ENGAJAMENTO | TEMPO MÉDIO DE ENGAJAMENTO (s) |
  TAXA DE REJEIÇÃO

Uso:
    python lucri_ga4_sheet_sync.py                        # ontem
    python lucri_ga4_sheet_sync.py 2026-09-01             # dia específico
    python lucri_ga4_sheet_sync.py 2026-09-01 2026-09-30  # intervalo
"""
import os
import socket
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cwbkids_commons import GA4Client, SheetsClient, date_br_display, date_br_input, parse_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

TAB = "GA4 - PÁGINAS"

HEADER = [
    "DATA", "PÁGINA", "SESSÕES", "USUÁRIOS", "NOVOS USUÁRIOS",
    "VISUALIZAÇÕES", "SESSÕES ENGAJADAS", "TAXA DE ENGAJAMENTO",
    "TEMPO MÉD. ENGAJAMENTO (s)", "TAXA DE REJEIÇÃO",
]

# Hostname + path → chave legível
PAGE_MAP = {
    ("lp.lucrifinancas.com.br", "/"):         "lp",
    ("lp.lucrifinancas.com.br", "/2"):         "lp2",
    ("type.lucrifinancas.com.br", "/"):        "typeform",
    ("lp.lucrifinancas.com.br", "/obrigado"):  "lp_obrigado",
    ("lucrifinancas.com.br", "/"):             "site",
    ("lucrifinancas.com.br", "/servicos"):     "site_servicos",
    ("lucrifinancas.com.br", "/sobre"):        "site_sobre",
    ("lucrifinancas.com.br", "/contato"):      "site_contato",
    ("lucrifinancas.com.br", "/ferramentas"):  "site_ferramentas",
}

PAGE_LABEL = {
    "lp":                   "LP padrão",
    "lp2":                  "LP curta",
    "typeform":             "TypeForm",
    "lp_obrigado":          "Obrigado (todos)",
    "lp_obrigado_lp":       "Obrigado (via LP padrão)",
    "lp_obrigado_lp2":      "Obrigado (via LP curta)",
    "lp_obrigado_outro":    "Obrigado (via outro)",
    "site":                 "Site — Home",
    "site_servicos":        "Site — Serviços",
    "site_sobre":           "Site — Sobre",
    "site_contato":         "Site — Contato",
    "site_ferramentas":     "Site — Ferramentas",
}

# Referrer normalizado → chave de origem do /obrigado
OBRIGADO_REFERRER_MAP = {
    "lp.lucrifinancas.com.br/":  "lp_obrigado_lp",
    "lp.lucrifinancas.com.br/2": "lp_obrigado_lp2",
}


def fetch_ga4(ga4, date_str):
    """Retorna dict {page_key: {metric: value}} para o dia dado."""
    url = ga4.ENDPOINT.format(property_id=ga4.property_id)
    resp = ga4.session.post(url, json={
        "dateRanges": [{"startDate": date_str, "endDate": date_str}],
        "dimensions": [{"name": "hostname"}, {"name": "pagePath"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "screenPageViews"},
            {"name": "engagedSessions"},
            {"name": "engagementRate"},
            {"name": "averageSessionDuration"},
            {"name": "bounceRate"},
        ],
        "limit": 100,
    }, timeout=30)
    resp.raise_for_status()

    result = {}
    for row in resp.json().get("rows", []):
        host = row["dimensionValues"][0]["value"]
        path = row["dimensionValues"][1]["value"]
        key = PAGE_MAP.get((host, path))
        if not key:
            continue
        vals = row["metricValues"]
        result[key] = {
            "sessions":           int(vals[0]["value"]),
            "users":              int(vals[1]["value"]),
            "new_users":          int(vals[2]["value"]),
            "page_views":         int(vals[3]["value"]),
            "engaged_sessions":   int(vals[4]["value"]),
            "engagement_rate":    round(float(vals[5]["value"]), 4),
            "avg_engagement_s":   round(float(vals[6]["value"]), 1),
            "bounce_rate":        round(float(vals[7]["value"]), 4),
        }
    return result


def fetch_obrigado_referrers(ga4, date_str):
    """Retorna dict {key: {metric: value}} para /obrigado quebrado por referrer."""
    url = ga4.ENDPOINT.format(property_id=ga4.property_id)
    resp = ga4.session.post(url, json={
        "dateRanges": [{"startDate": date_str, "endDate": date_str}],
        "dimensions": [{"name": "pageReferrer"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "screenPageViews"},
            {"name": "engagedSessions"},
            {"name": "engagementRate"},
            {"name": "averageSessionDuration"},
            {"name": "bounceRate"},
        ],
        "dimensionFilter": {
            "andGroup": {"expressions": [
                {"filter": {"fieldName": "hostname", "stringFilter": {"matchType": "EXACT", "value": "lp.lucrifinancas.com.br"}}},
                {"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "EXACT", "value": "/obrigado"}}},
            ]}
        },
        "limit": 20,
    }, timeout=30)
    resp.raise_for_status()

    buckets = {}
    for row in resp.json().get("rows", []):
        referrer = row["dimensionValues"][0]["value"]
        referrer_clean = referrer.replace("https://", "").replace("http://", "")
        # Compara por prefixo — o referrer pode ter UTMs/fbclid depois do path
        key = "lp_obrigado_outro"
        for prefix, mapped in OBRIGADO_REFERRER_MAP.items():
            if referrer_clean.startswith(prefix):
                key = mapped
                break
        vals = row["metricValues"]
        sessions = int(vals[0]["value"])
        if key not in buckets:
            buckets[key] = {"sessions": 0, "users": 0, "new_users": 0, "page_views": 0,
                            "engaged_sessions": 0, "_weighted_eng": 0.0, "_weighted_dur": 0.0,
                            "_weighted_bounce": 0.0}
        b = buckets[key]
        b["sessions"]        += sessions
        b["users"]           += int(vals[1]["value"])
        b["new_users"]       += int(vals[2]["value"])
        b["page_views"]      += int(vals[3]["value"])
        b["engaged_sessions"] += int(vals[4]["value"])
        b["_weighted_eng"]   += float(vals[5]["value"]) * sessions
        b["_weighted_dur"]   += float(vals[6]["value"]) * sessions
        b["_weighted_bounce"] += float(vals[7]["value"]) * sessions

    result = {}
    for key, b in buckets.items():
        s = b["sessions"] or 1
        result[key] = {
            "sessions":         b["sessions"],
            "users":            b["users"],
            "new_users":        b["new_users"],
            "page_views":       b["page_views"],
            "engaged_sessions": b["engaged_sessions"],
            "engagement_rate":  round(b["_weighted_eng"] / s, 4),
            "avg_engagement_s": round(b["_weighted_dur"] / s, 1),
            "bounce_rate":      round(b["_weighted_bounce"] / s, 4),
        }
    return result


def ensure_tab(sheets, sheet_id):
    try:
        result = sheets.values_get(sheet_id, f"{TAB}!A1:A1")
        if not result.get("values"):
            sheets.values_append(sheet_id, f"{TAB}!A1", [HEADER])
    except Exception:
        sheets.batch_update(sheet_id, [{"addSheet": {"properties": {"title": TAB}}}])
        sheets.values_append(sheet_id, f"{TAB}!A1", [HEADER])


def existing_keys(sheets, sheet_id):
    if getattr(sheets, "is_d1", False):
        return set()
    """Retorna set de (date_disp, page_key) já presentes na aba."""
    result = sheets.values_get(sheet_id, f"{TAB}!A2:B10000")
    return {(r[0], r[1]) for r in result.get("values", []) if len(r) >= 2}


def parse_dates():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    today = date.today()
    if len(args) == 0:
        return [today - timedelta(days=1)]
    if len(args) == 1:
        return [date.fromisoformat(args[0])]
    start = date.fromisoformat(args[0])
    end   = date.fromisoformat(args[1])
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def main():
    socket.setdefaulttimeout(30)
    env      = parse_env(ENV_PATH)
    sheets   = SheetsClient(env)
    sheet_id = env["SHEETS_ID_LUCRI_METRICAS"]

    # Usa o property ID da Lucri (separado do CWB Kids)
    env_lucri = dict(env)
    env_lucri["GA4_PROPERTY_ID"] = env["GA4_PROPERTY_ID_LUCRI"]
    ga4 = GA4Client(env_lucri)

    dates = parse_dates()
    print(f"Período: {dates[0]} → {dates[-1]}  ({len(dates)} dia(s))")

    ensure_tab(sheets, sheet_id)
    existing = existing_keys(sheets, sheet_id)

    rows_to_add = []
    for d in dates:
        date_disp = date_br_display(d)
        print(f"\n  {d.isoformat()}")
        data = fetch_ga4(ga4, d.isoformat())

        for key in ("lp", "lp2", "typeform", "lp_obrigado",
                    "site", "site_servicos", "site_sobre", "site_contato", "site_ferramentas"):
            if (date_disp, key) in existing:
                print(f"    [skip] {key}")
                continue
            m = data.get(key, {})
            rows_to_add.append([
                date_br_input(d),
                key,
                m.get("sessions", 0),
                m.get("users", 0),
                m.get("new_users", 0),
                m.get("page_views", 0),
                m.get("engaged_sessions", 0),
                m.get("engagement_rate", 0),
                m.get("avg_engagement_s", 0),
                m.get("bounce_rate", 0),
            ])
            status = "sem dados" if not m else f"{m.get('sessions',0)} sessões"
            print(f"    {PAGE_LABEL[key]:30} → {status}")

        # /obrigado quebrado por referrer (LP padrão vs LP curta)
        ref_data = fetch_obrigado_referrers(ga4, d.isoformat())
        for key in ("lp_obrigado_lp", "lp_obrigado_lp2", "lp_obrigado_outro"):
            if (date_disp, key) in existing:
                print(f"    [skip] {key}")
                continue
            m = ref_data.get(key, {})
            if not m:
                continue  # não grava linha vazia pra origens sem tráfego
            rows_to_add.append([
                date_br_input(d),
                key,
                m.get("sessions", 0),
                m.get("users", 0),
                m.get("new_users", 0),
                m.get("page_views", 0),
                m.get("engaged_sessions", 0),
                m.get("engagement_rate", 0),
                m.get("avg_engagement_s", 0),
                m.get("bounce_rate", 0),
            ])
            print(f"    {PAGE_LABEL[key]:30} → {m.get('sessions',0)} sessões")

    if rows_to_add:
        gid = sheets.get_tab_gid(sheet_id, TAB)
        sheets.append_and_format(
            sheet_id, gid, TAB, rows_to_add,
            percent_cols=[7, 9],   # TAXA DE ENGAJAMENTO, TAXA DE REJEIÇÃO
            currency_cols=[],
            date_col=0,
        )
        print(f"\n  {len(rows_to_add)} linha(s) inserida(s).")
    else:
        print("\n  Nenhuma linha nova.")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
