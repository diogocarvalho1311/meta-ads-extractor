"""
Sincroniza leads do Notion CRM (banco "Trafego Pago") para a planilha da Lucri.

O que faz:
  1. Aba CRM - LEADS: insere um registro por lead qualificado/desqualificado.
  2. META ADS (CAMPANHAS / CONJUNTOS DE ANÚNCIO / ANÚNCIOS): atualiza LEADS QUALIFICADOS,
     LEADS FECHADOS e CPLQ para leads com utm_source != google.
  3. GOOGLE ADS (CAMPANHAS / GRUPOS DE ANÚNCIO / PALAVRAS-CHAVE): atualiza as mesmas
     colunas para leads com utm_source == google. O grupo de anúncio é descoberto via
     lookup na aba PALAVRAS-CHAVE (mesma data/campanha/palavra-chave).

Regra de data: usa "Adicionado em" (created_time) — data em que o lead entrou.
LEADS QUALIFICADOS: Qualidade do Lead == "Qualificado"
LEADS FECHADOS: Status == "Fechado"

Uso:
    python lucri_crm_notion_sync.py            # dry-run (mostra contagens, só sincroniza CRM - LEADS)
    python lucri_crm_notion_sync.py --apply    # aplica tudo na planilha
"""
import os
import re
import sys
import socket
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cwbkids_commons import SheetsClient, date_br_display, date_br_input, parse_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

TAB_CRM = "CRM - LEADS"

# Abas Meta Ads
TAB_META_CAMP = "META ADS - CAMPANHAS"
TAB_META_CONJ = "META ADS - CONJUNTOS DE ANÚNCIO"
TAB_META_ANUN = "META ADS - ANÚNCIOS"

# Abas Google Ads
TAB_GADS_CAMP   = "GOOGLE ADS - CAMPANHAS"
TAB_GADS_GRUPO  = "GOOGLE ADS - GRUPOS DE ANÚNCIO"
TAB_GADS_PALAVRA = "GOOGLE ADS - PALAVRAS-CHAVE"

CRM_HEADER = [
    "NOTION ID", "DATA", "NOME", "EMPRESA", "TELEFONE",
    "DOR", "FATURAMENTO", "ORÇAMENTO", "QUEM CUIDA",
    "QUALIDADE DO LEAD", "STATUS",
    "UTM CAMPAIGN", "UTM SOURCE", "UTM MEDIUM", "UTM CONTENT", "UTM TERM",
]

DEFINIDOS = {"Qualificado", "Desqualificado"}
CLOSED_STATUS = {"Fechado"}


# ── helpers ───────────────────────────────────────────────────────────────────

def norm(s):
    return re.sub(r"\s+", "", (s or "").strip()).casefold()


def strip_keyword_wrapper(s):
    """Remove [colchetes] ou "aspas" de palavras-chave exatas/frase na planilha."""
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    if len(s) >= 2 and s[0] == "[" and s[-1] == "]":
        return s[1:-1]
    return s


def norm_keyword(s):
    return norm(strip_keyword_wrapper(s or ""))


def col_letter(idx):
    letters = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def ensure_column(sheets, sheet_id, gid, header, name, after_name, apply_changes):
    """Garante que `name` exista no cabeçalho, logo após `after_name`."""
    if name in header:
        return header.index(name)
    after_idx = header.index(after_name)
    idx = after_idx + 1
    if apply_changes:
        sheets.batch_update(sheet_id, [{
            "insertDimension": {
                "range": {"sheetId": gid, "dimension": "COLUMNS",
                           "startIndex": idx, "endIndex": idx + 1},
                "inheritFromBefore": False,
            }
        }])
    header.insert(idx, name)
    return idx


# ── Notion API ────────────────────────────────────────────────────────────────

def notion_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def fetch_leads(token, db_id):
    """Retorna leads com Qualidade do Lead definida OU com Status=Fechado."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    hdrs = notion_headers(token)
    payload = {
        "filter": {
            "or": [
                {"property": "Qualidade do Lead", "select": {"is_not_empty": True}},
                {"property": "Status", "status": {"equals": "Fechado"}},
            ]
        },
        "page_size": 100,
    }
    leads, cursor = [], None
    while True:
        if cursor:
            payload["start_cursor"] = cursor
        resp = requests.post(url, headers=hdrs, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        leads.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return leads


def prop_text(p):
    if p is None:
        return ""
    t = p.get("type", "")
    if t == "title":
        return p["title"][0]["plain_text"] if p["title"] else ""
    if t == "rich_text":
        return p["rich_text"][0]["plain_text"] if p["rich_text"] else ""
    if t == "phone_number":
        return p.get("phone_number") or ""
    if t == "select":
        return p["select"]["name"] if p.get("select") else ""
    if t == "status":
        return p["status"]["name"] if p.get("status") else ""
    if t == "created_time":
        return p.get("created_time", "")
    return ""


def parse_lead(page):
    props = page["properties"]
    created_raw = props.get("Adicionado em", {}).get("created_time", "")
    dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else None
    d  = dt.astimezone(timezone.utc).date() if dt else None
    qualidade = prop_text(props.get("Qualidade do Lead"))
    status_val = prop_text(props.get("Status"))
    # Inclui se Qualidade definida OU se já está Fechado (mesmo sem qualidade)
    if qualidade not in DEFINIDOS and status_val not in CLOSED_STATUS:
        return None
    return {
        "notion_id":    page["id"],
        "date":         d,
        "date_disp":    date_br_display(d) if d else "",
        "nome":         prop_text(props.get("Nome")),
        "empresa":      prop_text(props.get("Empresa")),
        "telefone":     prop_text(props.get("Telefone")),
        "dor":          prop_text(props.get("Dor")),
        "faturamento":  prop_text(props.get("Faturamento")),
        "orcamento":    prop_text(props.get("Orçamento")),
        "quem_cuida":   prop_text(props.get("Quem cuida")),
        "qualidade":    qualidade,
        "status":       status_val,
        "utm_campaign": prop_text(props.get("UTM Campaign")),
        "utm_source":   prop_text(props.get("UTM Source")),
        "utm_medium":   prop_text(props.get("UTM Medium")),
        "utm_content":  prop_text(props.get("UTM Content")),
        "utm_term":     prop_text(props.get("UTM Term")),
    }


# ── Aba CRM - LEADS ───────────────────────────────────────────────────────────

def sync_crm_tab(leads, sheets, sheet_id):
    try:
        result = sheets.values_get(sheet_id, f"{TAB_CRM}!A1:A1")
        if not result.get("values"):
            sheets.values_append(sheet_id, f"{TAB_CRM}!A1", [CRM_HEADER])
    except Exception:
        sheets.batch_update(sheet_id, [{"addSheet": {"properties": {"title": TAB_CRM}}}])
        sheets.values_append(sheet_id, f"{TAB_CRM}!A1", [CRM_HEADER])

    result  = sheets.values_get(sheet_id, f"{TAB_CRM}!A2:A10000")
    existing = set() if getattr(sheets, "is_d1", False) else {r[0] for r in result.get("values", []) if r}

    rows = []
    for lead in leads:
        if lead["notion_id"] in existing:
            continue
        rows.append([
            lead["notion_id"],
            date_br_input(lead["date"]) if lead["date"] else "",
            lead["nome"], lead["empresa"], lead["telefone"],
            lead["dor"], lead["faturamento"], lead["orcamento"], lead["quem_cuida"],
            lead["qualidade"], lead["status"],
            lead["utm_campaign"], lead["utm_source"], lead["utm_medium"],
            lead["utm_content"], lead["utm_term"],
        ])

    if rows:
        gid = sheets.get_tab_gid(sheet_id, TAB_CRM)
        sheets.append_and_format(sheet_id, gid, TAB_CRM, rows,
                                 percent_cols=[], currency_cols=[], date_col=1)
    print(f"  CRM - LEADS: {len(rows)} novo(s) lead(s) inserido(s)")
    return len(rows)


# ── Processamento de abas (LEADS QUALIFICADOS / FECHADOS / CPLQ) ─────────────

def process_tab(sheets, sheet_id, tab, key_cols, qualified_counts, closed_counts,
                apply_changes, keyword_col=None):
    """
    key_cols: índices (0-based) das colunas que formam a chave de match.
    keyword_col: se informado, esse índice usa norm_keyword() (remove aspas/colchetes).
    """
    r = sheets.values_get(sheet_id, f"{tab}!A1:Z10000")
    rows = r.get("values", [])
    if not rows:
        print(f"\n=== {tab} ===\n  (aba vazia, ignorada)")
        return
    header = list(rows[0])
    data_rows = rows[1:]
    n = len(header)
    n_rows = len(data_rows) + 1

    def counts_for(counts):
        values, matched = [0] * len(data_rows), 0
        for i, row in enumerate(data_rows):
            row = row + [""] * (n - len(row))
            key = tuple(
                (norm_keyword(row[c]) if c == keyword_col else norm(row[c]))
                for c in key_cols
            )
            cnt = counts.get(key, 0)
            values[i] = cnt
            if cnt:
                matched += cnt
        return values, matched

    lq_values, lq_matched = counts_for(qualified_counts)
    lf_values, lf_matched = counts_for(closed_counts)

    print(f"\n=== {tab} ===")
    print(f"  LEADS QUALIFICADOS: {sum(1 for v in lq_values if v)} linhas  (total: {lq_matched})")
    print(f"  LEADS FECHADOS:     {sum(1 for v in lf_values if v)} linhas  (total: {lf_matched})")

    if not apply_changes:
        return

    if getattr(sheets, "is_d1", False):
        # Atualiza as duas contagens juntas, somente nas linhas alteradas.
        # CPLQ e taxas sao gerados pelo D1; nao precisam de outras consultas.
        from d1_metricas import iso_date
        qualified_index = header.index("LEADS QUALIFICADOS")
        closed_index = header.index("LEADS FECHADOS")
        updates = []
        for i, original in enumerate(data_rows):
            row = original + [""] * (n - len(original))
            if float(row[qualified_index] or 0) == lq_values[i] and float(row[closed_index] or 0) == lf_values[i]:
                continue
            updates.append({"id": row[0], "data": iso_date(row[1]),
                            "leads_qualificados": lq_values[i], "leads_fechados": lf_values[i]})
        sheets.update_records(sheet_id, tab, updates)
        print(f"  D1: {len(updates)} linha(s) alteradas; CPLQ calculado pelo banco.")
        return

    gid = sheets.get_tab_gid(sheet_id, tab)

    lq_idx   = ensure_column(sheets, sheet_id, gid, header, "LEADS QUALIFICADOS", "LEADS", apply_changes)
    lf_idx   = ensure_column(sheets, sheet_id, gid, header, "LEADS FECHADOS", "LEADS QUALIFICADOS", apply_changes)
    cplq_idx = ensure_column(sheets, sheet_id, gid, header, "CPLQ", "CPA", apply_changes)
    invest_idx = header.index("INVESTIMENTO")

    lq_let, lf_let, cplq_let, inv_let = (
        col_letter(lq_idx), col_letter(lf_idx), col_letter(cplq_idx), col_letter(invest_idx)
    )

    sheets.values_update(sheet_id, f"{tab}!{lq_let}1:{lq_let}{n_rows}",
                         [["LEADS QUALIFICADOS"]] + [[v] for v in lq_values])
    sheets.values_update(sheet_id, f"{tab}!{lf_let}1:{lf_let}{n_rows}",
                         [["LEADS FECHADOS"]] + [[v] for v in lf_values])

    cplq_vals = ["CPLQ"] + [
        f'=IF({lq_let}{i}=0;"";{inv_let}{i}/{lq_let}{i})'
        for i in range(2, n_rows + 1)
    ]
    sheets.values_update(sheet_id, f"{tab}!{cplq_let}1:{cplq_let}{n_rows}",
                         [[v] for v in cplq_vals])

    sheets.batch_update(sheet_id, [
        {"repeatCell": {
            "range": {"sheetId": gid, "startRowIndex": 1, "endRowIndex": n_rows,
                      "startColumnIndex": lq_idx, "endColumnIndex": lq_idx + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }},
        {"repeatCell": {
            "range": {"sheetId": gid, "startRowIndex": 1, "endRowIndex": n_rows,
                      "startColumnIndex": lf_idx, "endColumnIndex": lf_idx + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }},
        {"repeatCell": {
            "range": {"sheetId": gid, "startRowIndex": 1, "endRowIndex": n_rows,
                      "startColumnIndex": cplq_idx, "endColumnIndex": cplq_idx + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "[$R$ -416]#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat",
        }},
    ])
    print(f"  aplicado. LQ={lq_let} LF={lf_let} CPLQ={cplq_let}")


# ── Meta Ads ──────────────────────────────────────────────────────────────────

def build_meta_counts(leads):
    camp_q, camp_f = {}, {}
    conj_q, conj_f = {}, {}
    anun_q, anun_f = {}, {}

    for l in leads:
        camp = norm(l["utm_campaign"])
        conj = norm(l["utm_content"])
        anun = norm(l["utm_term"])
        if not camp:
            continue
        dd = l["date_disp"]
        ck = (dd, camp)
        if l["qualidade"] == "Qualificado":
            camp_q[ck] = camp_q.get(ck, 0) + 1
            if conj:
                ak = (dd, camp, conj)
                conj_q[ak] = conj_q.get(ak, 0) + 1
                if anun:
                    dk = (dd, camp, conj, anun)
                    anun_q[dk] = anun_q.get(dk, 0) + 1
        if l["status"] in CLOSED_STATUS:
            camp_f[ck] = camp_f.get(ck, 0) + 1
            if conj:
                ak = (dd, camp, conj)
                conj_f[ak] = conj_f.get(ak, 0) + 1
                if anun:
                    dk = (dd, camp, conj, anun)
                    anun_f[dk] = anun_f.get(dk, 0) + 1

    return (camp_q, camp_f), (conj_q, conj_f), (anun_q, anun_f)


def process_meta_tabs(meta_leads, sheets, sheet_id, apply_changes):
    (camp_q, camp_f), (conj_q, conj_f), (anun_q, anun_f) = build_meta_counts(meta_leads)

    process_tab(sheets, sheet_id, TAB_META_CAMP,
                key_cols=[1, 2], qualified_counts=camp_q, closed_counts=camp_f,
                apply_changes=apply_changes)
    process_tab(sheets, sheet_id, TAB_META_CONJ,
                key_cols=[1, 2, 3], qualified_counts=conj_q, closed_counts=conj_f,
                apply_changes=apply_changes)
    process_tab(sheets, sheet_id, TAB_META_ANUN,
                key_cols=[1, 2, 3, 4], qualified_counts=anun_q, closed_counts=anun_f,
                apply_changes=apply_changes)


# ── Google Ads ────────────────────────────────────────────────────────────────

def build_grupo_lookup(sheets, sheet_id):
    """(date_disp, campanha, palavra_chave) -> nome original do grupo de anúncio."""
    r = sheets.values_get(sheet_id, f"{TAB_GADS_PALAVRA}!A1:Z10000")
    rows = r.get("values", [])
    if not rows:
        return {}
    header = rows[0]
    idx = {h.strip().upper(): i for i, h in enumerate(header)}
    date_i  = idx.get("DATA", 1)
    camp_i  = idx.get("CAMPANHA", 2)
    grupo_i = idx.get("GRUPO DE ANÚNCIO", 3)
    kw_i    = idx.get("PALAVRA-CHAVE", 4)
    lookup = {}
    for row in rows[1:]:
        if len(row) <= max(date_i, camp_i, grupo_i, kw_i):
            continue
        key = (norm(row[date_i]), norm(row[camp_i]), norm_keyword(row[kw_i]))
        lookup[key] = row[grupo_i]
    return lookup


def build_google_counts(google_leads, grupo_lookup):
    camp_q, camp_f = {}, {}
    grupo_q, grupo_f = {}, {}
    palavra_q, palavra_f = {}, {}
    sem_grupo = []

    for l in google_leads:
        camp = norm(l["utm_campaign"])
        kw   = norm(l["utm_term"])
        if not camp:
            continue
        dd = l["date_disp"]
        ck = (dd, camp)

        if l["qualidade"] == "Qualificado":
            camp_q[ck] = camp_q.get(ck, 0) + 1
            if kw:
                pk = (dd, camp, kw)
                palavra_q[pk] = palavra_q.get(pk, 0) + 1
                grupo_nome = grupo_lookup.get((dd, camp, kw))
                if grupo_nome:
                    gk = (dd, camp, norm(grupo_nome))
                    grupo_q[gk] = grupo_q.get(gk, 0) + 1
                else:
                    sem_grupo.append(l)

        if l["status"] in CLOSED_STATUS:
            camp_f[ck] = camp_f.get(ck, 0) + 1
            if kw:
                pk = (dd, camp, kw)
                palavra_f[pk] = palavra_f.get(pk, 0) + 1
                grupo_nome = grupo_lookup.get((dd, camp, kw))
                if grupo_nome:
                    gk = (dd, camp, norm(grupo_nome))
                    grupo_f[gk] = grupo_f.get(gk, 0) + 1

    return (camp_q, camp_f), (grupo_q, grupo_f), (palavra_q, palavra_f), sem_grupo


def process_google_tabs(google_leads, sheets, sheet_id, apply_changes):
    grupo_lookup = build_grupo_lookup(sheets, sheet_id)
    (camp_q, camp_f), (grupo_q, grupo_f), (palavra_q, palavra_f), sem_grupo = \
        build_google_counts(google_leads, grupo_lookup)

    if sem_grupo:
        print(f"\n  [aviso] {len(sem_grupo)} lead(s) sem grupo de anúncio encontrado na aba PALAVRAS-CHAVE:")
        for l in sem_grupo:
            print(f"    - {l['nome']} ({l['date_disp']}, {l['utm_campaign']!r}, {l['utm_term']!r})")

    process_tab(sheets, sheet_id, TAB_GADS_CAMP,
                key_cols=[1, 2], qualified_counts=camp_q, closed_counts=camp_f,
                apply_changes=apply_changes)
    process_tab(sheets, sheet_id, TAB_GADS_GRUPO,
                key_cols=[1, 2, 3], qualified_counts=grupo_q, closed_counts=grupo_f,
                apply_changes=apply_changes)
    # col 4 = PALAVRA-CHAVE (pode ter [colchetes]/"aspas"), keyword_col=4
    process_tab(sheets, sheet_id, TAB_GADS_PALAVRA,
                key_cols=[1, 2, 4], qualified_counts=palavra_q, closed_counts=palavra_f,
                apply_changes=apply_changes, keyword_col=4)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    socket.setdefaulttimeout(30)
    apply_changes = "--apply" in sys.argv
    env      = parse_env(ENV_PATH)
    token    = env["NOTION_LUCRI_API_KEY"]
    db_id    = env["NOTION_LUCRI_CRM_DB_ID"]
    sheets   = SheetsClient(env)
    sheet_id = env["SHEETS_ID_LUCRI_METRICAS"]

    print("Buscando leads do Notion...")
    raw_leads = fetch_leads(token, db_id)
    print(f"  {len(raw_leads)} lead(s) com qualidade definida encontrado(s)")

    leads = [l for l in (parse_lead(p) for p in raw_leads) if l]
    print(f"  {len(leads)} lead(s) válido(s) após parse")

    qualif = sum(1 for l in leads if l["qualidade"] == "Qualificado")
    desq   = sum(1 for l in leads if l["qualidade"] == "Desqualificado")
    fechados = sum(1 for l in leads if l["status"] in CLOSED_STATUS)
    print(f"  Qualificados: {qualif}  |  Desqualificados: {desq}  |  Fechados: {fechados}")

    meta_leads   = [l for l in leads if norm(l["utm_source"]) != "google"]
    google_leads = [l for l in leads if norm(l["utm_source"]) == "google"]
    print(f"  Meta: {len(meta_leads)} leads  |  Google: {len(google_leads)} leads")

    print("\nAtualizando CRM - LEADS...")
    if apply_changes:
        sync_crm_tab(leads, sheets, sheet_id)
    else:
        print("  Simulacao: CRM nao alterado. Use --apply para gravar.")

    print("\nProcessando Meta Ads...")
    process_meta_tabs(meta_leads, sheets, sheet_id, apply_changes)

    print("\nProcessando Google Ads...")
    process_google_tabs(google_leads, sheets, sheet_id, apply_changes)

    if not apply_changes:
        print("\n[dry-run] Colunas de leads NÃO foram modificadas. Rode com --apply para gravar.")
    else:
        print("\nConcluído.")


if __name__ == "__main__":
    main()
