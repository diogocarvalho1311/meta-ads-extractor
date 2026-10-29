"""
Puxa contagens de quiz_step_view por etapa do GA4 da Lucri e grava na planilha.

Colunas gravadas por dia (formato largo — um valor por etapa):
  DATA | NOME | WHATSAPP | EMPRESA | FATURAMENTO | DESAFIO | OBRIGADO

Uso:
    python lucri_ga4_quiz_sync.py                        # ontem
    python lucri_ga4_quiz_sync.py 2026-09-01             # dia específico
    python lucri_ga4_quiz_sync.py 2026-09-01 2026-09-30  # intervalo
"""
import os
import socket
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cwbkids_commons import GA4Client, SheetsClient, date_br_display, date_br_input, parse_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

TAB = "GA4 - QUIZ LP PADRÃO"

STEPS = ["nome", "whatsapp", "empresa", "faturamento", "desafio"]

HEADER = ["DATA"] + [s.upper() for s in STEPS] + ["OBRIGADO"]


def fetch_quiz_steps(ga4, date_str):
    """Retorna dict {step_name: count} para quiz_step_view no dia dado."""
    url = ga4.ENDPOINT.format(property_id=ga4.property_id)
    resp = ga4.session.post(url, json={
        "dateRanges": [{"startDate": date_str, "endDate": date_str}],
        "dimensions": [{"name": "customEvent:step_name"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "stringFilter": {"matchType": "EXACT", "value": "quiz_step_view"},
            }
        },
        "limit": 20,
    }, timeout=30)
    resp.raise_for_status()

    result = {}
    for row in resp.json().get("rows", []):
        step = row["dimensionValues"][0]["value"]
        count = int(row["metricValues"][0]["value"])
        result[step] = count
    return result


def fetch_obrigado(ga4, date_str):
    """Retorna page_views da página /obrigado no dia dado."""
    url = ga4.ENDPOINT.format(property_id=ga4.property_id)
    resp = ga4.session.post(url, json={
        "dateRanges": [{"startDate": date_str, "endDate": date_str}],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [{"name": "screenPageViews"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "pagePath",
                "stringFilter": {"matchType": "EXACT", "value": "/obrigado"},
            }
        },
        "limit": 5,
    }, timeout=30)
    resp.raise_for_status()

    rows = resp.json().get("rows", [])
    if not rows:
        return 0
    return sum(int(r["metricValues"][0]["value"]) for r in rows)


def ensure_tab(sheets, sheet_id):
    try:
        result = sheets.values_get(sheet_id, f"{TAB}!A1:A1")
        if not result.get("values"):
            sheets.values_append(sheet_id, f"{TAB}!A1", [HEADER])
    except Exception:
        sheets.batch_update(sheet_id, [{"addSheet": {"properties": {"title": TAB}}}])
        sheets.values_append(sheet_id, f"{TAB}!A1", [HEADER])


def existing_dates(sheets, sheet_id):
    if getattr(sheets, "is_d1", False):
        return set()
    result = sheets.values_get(sheet_id, f"{TAB}!A2:A10000")
    return {r[0] for r in result.get("values", []) if r}


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

    env_lucri = dict(env)
    env_lucri["GA4_PROPERTY_ID"] = env["GA4_PROPERTY_ID_LUCRI"]
    ga4 = GA4Client(env_lucri)

    dates = parse_dates()
    print(f"Período: {dates[0]} → {dates[-1]}  ({len(dates)} dia(s))")

    ensure_tab(sheets, sheet_id)
    existing = existing_dates(sheets, sheet_id)

    rows_to_add = []
    for d in dates:
        date_disp = date_br_display(d)
        if date_disp in existing:
            print(f"  [skip] {d.isoformat()}")
            continue

        print(f"\n  {d.isoformat()}")
        steps_data = fetch_quiz_steps(ga4, d.isoformat())
        obrigado   = fetch_obrigado(ga4, d.isoformat())

        row = [date_br_input(d)]
        for step in STEPS:
            count = steps_data.get(step, 0)
            row.append(count)
            print(f"    {step:12} → {count}")
        row.append(obrigado)
        print(f"    {'obrigado':12} → {obrigado}")
        rows_to_add.append(row)

    if rows_to_add:
        gid = sheets.get_tab_gid(sheet_id, TAB)
        sheets.append_and_format(
            sheet_id, gid, TAB, rows_to_add,
            percent_cols=[],
            currency_cols=[],
            date_col=0,
        )
        print(f"\n  {len(rows_to_add)} linha(s) inserida(s).")
    else:
        print("\n  Nenhuma linha nova.")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
