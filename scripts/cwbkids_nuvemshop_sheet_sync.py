"""
Sincroniza pedidos pagos diários da loja Nuvemshop (CWB Kids) para a aba
NUVEMSHOP da planilha SHEETS_ID_CWBKIDS_METRICAS.

Colunas preenchidas automaticamente: DATA | PEDIDOS TOTAIS DA LOJA | RECEITA TOTAL DA LOJA
Coluna manual: SESSÕES (a API da Nuvemshop não expõe sessões/visitas).

Uso:
    python cwbkids_nuvemshop_sheet_sync.py                        # catch-up
    python cwbkids_nuvemshop_sheet_sync.py 2026-06-20             # data específica
    python cwbkids_nuvemshop_sheet_sync.py 2026-06-05 2026-06-20  # intervalo
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from urllib.parse import quote

import requests
from cwbkids_commons import SheetsClient, date_br_display, date_br_input, parse_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cwbkids_nuvemshop_state.json")

TAB = "NUVEMSHOP"


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"last_synced_date": None}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_paid_orders(store_id, token, target_date):
    headers = {
        "Authentication": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "CWBKids (contato@example.com)",
    }
    start = datetime.combine(target_date, datetime.min.time()).isoformat()
    end   = datetime.combine(target_date, datetime.max.time()).isoformat()
    orders, page = [], 1
    while True:
        resp = requests.get(
            f"https://api.nuvemshop.com.br/v1/{store_id}/orders",
            headers=headers,
            params={"payment_status": "paid", "created_at_min": start,
                    "created_at_max": end, "per_page": 200, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        orders.extend(batch)
        if len(batch) < 200:
            break
        page += 1
    return orders


def read_sheet_state(sheets, sheet_id):
    """Retorna (synced, row_map).
    synced: set de display-dates com coluna B preenchida.
    row_map: dict {display_date: row_number} para todas as linhas."""
    result = sheets.values_get(sheet_id, f"{TAB}!A2:C10000")
    rows = result.get("values", [])
    synced, row_map = set(), {}
    for i, row in enumerate(rows):
        if not row:
            continue
        display = row[0]
        row_num = i + 2  # +2: cabeçalho + 1-based
        row_map[display] = row_num
        if len(row) >= 2 and row[1] != "":
            synced.add(display)
    return synced, row_map


def sync_day(target_date, store_id, token, sheets, sheet_id, synced, row_map):
    display = date_br_display(target_date)
    if display in synced:
        print(f"--- {target_date.isoformat()} --- já sincronizado.")
        return

    orders = fetch_paid_orders(store_id, token, target_date)
    pedidos = len(orders)
    receita = sum(float(o.get("total", 0) or 0) for o in orders)

    if getattr(sheets, "is_d1", False):
        sheets.upsert_records(sheet_id, TAB, [{
            "data": target_date.isoformat(), "pedidos_totais_da_loja": pedidos,
            "receita_total_da_loja": receita,
        }])
        synced.add(display)
        print(f"--- {target_date.isoformat()} --- D1: {pedidos} pedido(s), R$ {receita:.2f}")
        return

    gid = sheets.get_tab_gid(sheet_id, TAB)

    if display in row_map:
        # Linha existe mas sem dados — atualiza colunas B e C
        row_num = row_map[display]
        sheets.values_batch_update(sheet_id, [
            {"range": f"{TAB}!B{row_num}:C{row_num}", "values": [[pedidos, receita]]},
        ], value_input_option="USER_ENTERED")
        # Formata coluna C como moeda
        sheets.batch_update(sheet_id, [{
            "repeatCell": {
                "range": {"sheetId": gid, "startRowIndex": row_num - 1, "endRowIndex": row_num,
                           "startColumnIndex": 2, "endColumnIndex": 3},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "[$R$ -416]#,##0.00"}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        }])
        print(f"--- {target_date.isoformat()} --- atualizado: {pedidos} pedido(s), R$ {receita:.2f}")
    else:
        sheets.append_and_format(
            sheet_id, gid, TAB,
            [[date_br_input(target_date), pedidos, receita, ""]],
            percent_cols=[], currency_cols=[2], date_col=0,
        )
        print(f"--- {target_date.isoformat()} --- {pedidos} pedido(s), R$ {receita:.2f}")


def main():
    yesterday = date.today() - timedelta(days=1)
    if len(sys.argv) == 3:
        start_date, end_date = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
    elif len(sys.argv) == 2:
        start_date = end_date = date.fromisoformat(sys.argv[1])
    else:
        state = load_state()
        last = state.get("last_synced_date")
        start_date = date.fromisoformat(last) + timedelta(days=1) if last else yesterday
        end_date = yesterday

    if start_date > end_date:
        print(f"Nada a sincronizar (último dia: {start_date - timedelta(days=1)}).")
        return

    env = parse_env(ENV_PATH)
    sheets = SheetsClient(env)
    sheet_id = env["SHEETS_ID_CWBKIDS_METRICAS"]
    synced, row_map = read_sheet_state(sheets, sheet_id)

    d = start_date
    while d <= end_date:
        sync_day(d, env["NUVEMSHOP_STORE_ID"], env["NUVEMSHOP_ACCESS_TOKEN"],
                 sheets, sheet_id, synced, row_map)
        d += timedelta(days=1)

    # Ordena aba por DATA
    gid = sheets.get_tab_gid(sheet_id, TAB)
    sheets.batch_update(sheet_id, [{
        "sortRange": {
            "range": {"sheetId": gid, "startRowIndex": 1, "startColumnIndex": 0},
            "sortSpecs": [{"dimensionIndex": 0, "sortOrder": "ASCENDING"}],
        }
    }])
    save_state({"last_synced_date": end_date.isoformat()})


if __name__ == "__main__":
    main()
