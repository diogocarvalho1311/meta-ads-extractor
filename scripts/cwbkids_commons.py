"""
Utilitários compartilhados entre os scripts de sync da CWB Kids.
Importado por cwbkids_meta_sheet_sync.py, cwbkids_google_ads_sheet_sync.py
e cwbkids_nuvemshop_sheet_sync.py.
"""
import re
import socket
import time
from urllib.parse import quote

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

MONTH_ABBR_PT = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}


def parse_env(path):
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^([A-Z0-9_]+)\s*=\s*(.*)$', line.rstrip("\n"))
            if not m:
                continue
            key, raw = m.group(1), m.group(2).strip()
            if raw.startswith('"'):
                raw = raw[1:]
                end = raw.find('"')
                val = raw[:end] if end != -1 else raw
            elif raw.startswith("'"):
                raw = raw[1:]
                end = raw.find("'")
                val = raw[:end] if end != -1 else raw
            else:
                val = raw
            env[key] = val
    return env


def safe_div(a, b):
    return a / b if b else 0.0


def date_br_input(d):
    return d.strftime("%d/%m/%Y")


def date_br_display(d):
    from d1_metricas import d1_enabled
    if d1_enabled():
        return d.strftime("%d/%m/%Y")
    return f"{d.day}/{MONTH_ABBR_PT[d.month]}."


class GoogleSheetsClient:
    """Cliente mínimo da API do Sheets via requests, sem httplib2."""

    BASE = "https://sheets.googleapis.com/v4/spreadsheets"

    def __init__(self, env):
        creds = service_account.Credentials.from_service_account_info(
            {
                "type": "service_account",
                "client_email": env["SHEETS_SERVICE_ACCOUNT_EMAIL"],
                "private_key": env["SHEETS_PRIVATE_KEY"].replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            },
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self.session = AuthorizedSession(creds)

    def get(self, sheet_id):
        r = self.session.get(f"{self.BASE}/{sheet_id}", timeout=60)
        r.raise_for_status()
        return r.json()

    def _request(self, method, url, **kwargs):
        """Executa requisição com retry automático em caso de 429."""
        for attempt in range(5):
            r = getattr(self.session, method)(url, **kwargs)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10)) + attempt * 5
                print(f"    [429] aguardando {wait}s antes de tentar novamente...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        r.raise_for_status()
        return r

    def values_get(self, sheet_id, range_, value_render_option=None):
        params = {"valueRenderOption": value_render_option} if value_render_option else {}
        r = self._request("get", f"{self.BASE}/{sheet_id}/values/{quote(range_, safe='')}", params=params, timeout=60)
        return r.json()

    def values_update(self, sheet_id, range_, rows, value_input_option="USER_ENTERED"):
        """Sobrescreve os valores a partir do canto superior esquerdo de range_.
        Use value_input_option="RAW" pra evitar que o Sheets converta
        strings numericas (ex: SKUs com zero a esquerda) em numero."""
        r = self._request("put",
            f"{self.BASE}/{sheet_id}/values/{quote(range_, safe='')}",
            params={"valueInputOption": value_input_option},
            json={"values": rows},
            timeout=60,
        )
        return r.json()

    def values_batch_update(self, sheet_id, data, value_input_option="RAW"):
        """data: lista de {'range': 'Aba!B5', 'values': [[valor]]}. Grava
        varias celulas/faixas em uma unica chamada."""
        r = self._request("post",
            f"{self.BASE}/{sheet_id}/values:batchUpdate",
            json={"valueInputOption": value_input_option, "data": data},
            timeout=60,
        )
        return r.json()

    def values_append(self, sheet_id, range_, rows, value_input_option="USER_ENTERED"):
        r = self._request("post",
            f"{self.BASE}/{sheet_id}/values/{quote(range_, safe='')}:append",
            params={"valueInputOption": value_input_option, "insertDataOption": "INSERT_ROWS"},
            json={"values": rows},
            timeout=60,
        )
        return r.json()

    def batch_update(self, sheet_id, body):
        r = self._request("post", f"{self.BASE}/{sheet_id}:batchUpdate", json={"requests": body}, timeout=60)
        return r.json()

    def get_tab_gid(self, sheet_id, tab):
        meta = self.get(sheet_id)
        for s in meta["sheets"]:
            if s["properties"]["title"] == tab:
                return s["properties"]["sheetId"]
        raise ValueError(f"Aba não encontrada: '{tab}'")

    def existing_keys(self, sheet_id, tab):
        """Retorna set de (col_A, col_B) já presentes — usado para dedup por (ID, data_display)."""
        result = self.values_get(sheet_id, f"{tab}!A2:B10000")
        return {(row[0], row[1]) for row in result.get("values", []) if len(row) >= 2}

    def append_and_format(self, sheet_id, gid, tab, rows, percent_cols, currency_cols, date_col=1):
        if not rows:
            return
        result = self.values_append(sheet_id, f"{tab}!A1", rows)
        updated = result["updates"]["updatedRange"]
        m = re.search(r"![A-Z]+(\d+):[A-Z]+(\d+)", updated)
        start_row, end_row = int(m.group(1)), int(m.group(2))

        fmt = []
        if date_col is not None:
            fmt.append({
                "repeatCell": {
                    "range": {"sheetId": gid, "startRowIndex": start_row - 1, "endRowIndex": end_row,
                               "startColumnIndex": date_col, "endColumnIndex": date_col + 1},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": 'd"/"mmm'}}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            })
        for col in percent_cols:
            fmt.append({
                "repeatCell": {
                    "range": {"sheetId": gid, "startRowIndex": start_row - 1, "endRowIndex": end_row,
                               "startColumnIndex": col, "endColumnIndex": col + 1},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            })
        for col in currency_cols:
            fmt.append({
                "repeatCell": {
                    "range": {"sheetId": gid, "startRowIndex": start_row - 1, "endRowIndex": end_row,
                               "startColumnIndex": col, "endColumnIndex": col + 1},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "[$R$ -416]#,##0.00"}}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            })
        self.batch_update(sheet_id, fmt)

    def sort_tabs_by_date(self, sheet_id, tabs, date_col_idx=1):
        body = []
        for tab in tabs:
            gid = self.get_tab_gid(sheet_id, tab)
            body.append({
                "sortRange": {
                    "range": {"sheetId": gid, "startRowIndex": 1, "startColumnIndex": 0},
                    "sortSpecs": [
                        {"dimensionIndex": date_col_idx, "sortOrder": "ASCENDING"},
                        {"dimensionIndex": 0, "sortOrder": "ASCENDING"},
                    ],
                }
            })
        self.batch_update(sheet_id, body)


class GA4Client:
    """
    Busca métricas de funil de conversão do GA4 por campanha/dia.
    Usa a mesma service account dos Sheets (scope analytics.readonly).
    """

    ENDPOINT = "https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"

    def __init__(self, env):
        socket.setdefaulttimeout(30)   # cobre o refresh do token OAuth2 tb
        creds = service_account.Credentials.from_service_account_info(
            {
                "type": "service_account",
                "client_email": env["SHEETS_SERVICE_ACCOUNT_EMAIL"],
                "private_key": env["SHEETS_PRIVATE_KEY"].replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            },
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        self.session = AuthorizedSession(creds)
        self.property_id = env["GA4_PROPERTY_ID"]

    def fetch_by_campaign(self, date_str, campaign_dimension):
        """
        Retorna dict {nome_campanha: {page_views, add_to_cart, begin_checkout, purchases, revenue}}
        para o dia date_str (AAAA-MM-DD).

        campaign_dimension:
          - 'sessionManualCampaignName'     → Meta Ads (utm_campaign = nome da campanha)
          - 'sessionGoogleAdsCampaignName'  → Google Ads (autotagging via gclid)
        """
        url = self.ENDPOINT.format(property_id=self.property_id)

        # Chamada 1: sessões, compras e receita por campanha
        resp1 = self.session.post(url, json={
            "dateRanges": [{"startDate": date_str, "endDate": date_str}],
            "dimensions": [{"name": campaign_dimension}],
            "metrics": [
                {"name": "sessions"},
                {"name": "ecommercePurchases"},
                {"name": "purchaseRevenue"},
            ],
        }, timeout=30)
        resp1.raise_for_status()

        result = {}
        for row in resp1.json().get("rows", []):
            campaign = row["dimensionValues"][0]["value"]
            if campaign in ("(not set)", "(other)", ""):
                continue
            result[campaign] = {
                "page_views": float(row["metricValues"][0]["value"]),
                "add_to_cart": 0.0,
                "begin_checkout": 0.0,
                "purchases": float(row["metricValues"][1]["value"]),
                "revenue": float(row["metricValues"][2]["value"]),
            }

        # Chamada 2: contagem de add_to_cart e begin_checkout por campanha
        resp2 = self.session.post(url, json={
            "dateRanges": [{"startDate": date_str, "endDate": date_str}],
            "dimensions": [{"name": campaign_dimension}, {"name": "eventName"}],
            "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "eventName",
                    "inListFilter": {"values": ["add_to_cart", "begin_checkout"]},
                }
            },
        }, timeout=30)
        resp2.raise_for_status()

        for row in resp2.json().get("rows", []):
            campaign = row["dimensionValues"][0]["value"]
            event = row["dimensionValues"][1]["value"]
            count = float(row["metricValues"][0]["value"])
            if campaign in ("(not set)", "(other)", ""):
                continue
            if campaign not in result:
                result[campaign] = {
                    "page_views": 0.0, "add_to_cart": 0.0,
                    "begin_checkout": 0.0, "purchases": 0.0, "revenue": 0.0,
                }
            if event == "add_to_cart":
                result[campaign]["add_to_cart"] = count
            elif event == "begin_checkout":
                result[campaign]["begin_checkout"] = count

        return result


def SheetsClient(env):
    """Seleciona o destino das metricas; outras planilhas continuam no Google."""
    from d1_metricas import D1MetricsClient, d1_enabled
    import os
    backend = os.environ.get("METRICAS_BACKEND", env.get("METRICAS_BACKEND", "sheets")).lower()
    if backend not in ("sheets", "d1"):
        raise ValueError("METRICAS_BACKEND deve ser sheets ou d1.")
    google = GoogleSheetsClient(env)
    return D1MetricsClient(env, google) if d1_enabled(env) else google
