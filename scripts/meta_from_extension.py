"""
Recebe dados exportados pela extensão Chrome Meta Ads Extractor e grava nas planilhas.

Uso:
    1. Na extensão, clique "Exportar tudo → JSON"
    2. Execute: python scripts/meta_from_extension.py
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cwbkids_commons import GA4Client, SheetsClient, date_br_display, date_br_input, parse_env, safe_div

# ── Mapeamento account_id → configuração do cliente ──────────────────────────
CLIENTES = {
    "1111111111111111": {
        "nome":        "Lucri Finanças",
        "sheet_env":   "SHEETS_ID_LUCRI_METRICAS",
        "id_map_file": "lucri_meta_manual_id_map.json",
        "key_prefix":  "L",   # prefixo da chave no id_map
        "id_prefix":   "Lm",  # prefixo dos IDs gerados
        "usa_ga4":     False,
        "destino_link": lambda cname: "NÃO" if "FormNativo" in cname else "SIM",
    },
    "222222222222222": {
        "nome":        "CWB Kids",
        "sheet_env":   "SHEETS_ID_CWBKIDS_METRICAS",
        "id_map_file": "cwbkids_meta_id_map.json",
        "key_prefix":  "M",   # igual ao cwbkids_meta_manual_entry.py
        "id_prefix":   "m",   # igual ao cwbkids_meta_manual_entry.py
        "usa_ga4":     True,
        "destino_link": lambda cname: "SIM",
    },
}

TAB_C = "META ADS - CAMPANHAS"
TAB_A = "META ADS - CONJUNTOS DE ANÚNCIO"
TAB_D = "META ADS - ANÚNCIOS"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# ── Helpers de ID (mesma lógica dos scripts manuais) ─────────────────────────

def load_id_map(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"campaigns": {}, "adsets": {}, "ads": {}}

def save_id_map(m, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

def get_id(id_map, level, key, prefix):
    bucket = id_map[level]
    if key in bucket:
        return bucket[key]
    nums = [int(v[len(prefix):]) for v in bucket.values()
            if v.startswith(prefix) and v[len(prefix):].isdigit()]
    n = max(nums, default=0) + 1
    sid = f"{prefix}{n}"
    bucket[key] = sid
    return sid

OBJETIVO_MAP = {
    "OUTCOME_LEADS":    "LEADS",
    "OUTCOME_TRAFFIC":  "TRAFEGO",
    "OUTCOME_AWARENESS":"AWARENESS",
    "OUTCOME_SALES":    "VENDAS",
    "LEAD_GENERATION":  "LEADS",
    "LINK_CLICKS":      "TRAFEGO",
}

def normalizar_objetivo(obj):
    return OBJETIVO_MAP.get(obj, obj)

def audience_level(name):
    for k in ("FRIO", "MORNO", "QUENTE"):
        if k in name.upper():
            return k
    return ""

def destino_link(cname):
    return "NÃO" if "FormNativo" in cname else "SIM"

# ── Datas presentes no payload ────────────────────────────────────────────────

def get_dates(payload) -> list:
    """Retorna lista ordenada de datas únicas no payload.

    JSONs novos têm campo 'date' (YYYY-MM-DD) em cada item (time_increment=1).
    JSONs antigos não têm — usa fallback pelo datePreset para preset single-day.
    """
    dates = set()
    for key in ("campanhas", "conjuntos", "anuncios"):
        for item in payload.get(key, []):
            if "date" in item:
                dates.add(date.fromisoformat(item["date"]))
    if dates:
        return sorted(dates)
    # fallback: preset single-day
    today = date.today()
    mapping = {"yesterday": today - timedelta(days=1), "today": today}
    preset = payload.get("datePreset", "")
    if preset not in mapping:
        raise ValueError(
            f"Preset '{preset}' não é single-day e o JSON não tem campo 'date' por item.\n"
            "Reexporte com a extensão atualizada ou use preset 'Ontem'/'Hoje'."
        )
    return [mapping[preset]]

# ── Inserção Lucri ────────────────────────────────────────────────────────────

def _items_for(items, d):
    """Filtra itens pela data (campo 'date'). Se não houver campo, retorna tudo."""
    if items and "date" in items[0]:
        iso = d.isoformat()
        return [x for x in items if x.get("date") == iso]
    return items


def process_lucri(payload, sheets, sheet_id, id_map, cfg):
    kp = cfg["key_prefix"]
    ip = cfg["id_prefix"]
    dl = cfg["destino_link"]

    for d in get_dates(payload):
        date_in   = date_br_input(d)
        date_disp = date_br_display(d)
        print(f"\n=== {d.isoformat()} ===")

        existing = sheets.existing_keys(sheet_id, TAB_C)
        camp_ids = {}
        rows     = []
        for c in _items_for(payload["campanhas"], d):
            cname = c["nome"]
            imp, cli, pv, leads, spend = c["impressoes"], c["cliques"], c.get("pv", 0), c["leads"], c["gasto"]
            obj = normalizar_objetivo(c.get("objetivo", "LEADS"))
            sid = get_id(id_map, "campaigns", f"{kp}:{cname}", ip)
            camp_ids[cname] = sid
            if (sid, date_disp) in existing:
                print(f"  [skip] campanha {cname}"); continue
            rows.append([sid, date_in, cname, cname, obj, dl(cname),
                         imp, cli, pv, leads,
                         0,  # LEADS QUALIFICADOS (manual, ver lucri_leads_qualificados_sync.py)
                         0,  # LEADS FECHADOS (manual, ver lucri_leads_qualificados_sync.py)
                         safe_div(cli, imp), safe_div(pv, cli), safe_div(leads, pv),
                         safe_div(spend, cli), safe_div(spend, imp)*1000, safe_div(spend, leads),
                         "",  # CPLQ
                         spend])
        gid = sheets.get_tab_gid(sheet_id, TAB_C)
        sheets.append_and_format(sheet_id, gid, TAB_C, rows,
                                 percent_cols=[12,13,14], currency_cols=[15,16,17,19])
        print(f"  CAMPANHAS: {len(rows)} linha(s)")

        existing  = sheets.existing_keys(sheet_id, TAB_A)
        adset_ids = {}
        rows      = []
        for c in _items_for(payload["conjuntos"], d):
            cname, aname = c["campanha"], c["nome"]
            imp, reach, cli, freq, pv, leads, spend = (
                c["impressoes"], c["alcance"], c["cliques"],
                c.get("frequencia", 0), c.get("pv", 0), c["leads"], c["gasto"])
            c_sid = camp_ids.get(cname) or get_id(id_map, "campaigns", f"{kp}:{cname}", ip)
            sid   = get_id(id_map, "adsets", f"{kp}:{cname}:{aname}", f"{c_sid}.")
            adset_ids[(cname, aname)] = sid
            if (sid, date_disp) in existing:
                print(f"  [skip] conjunto {aname}"); continue
            rows.append([sid, date_in, cname, aname, aname, audience_level(cname),
                         imp, reach, cli, pv, leads,
                         0,  # LEADS QUALIFICADOS (manual, ver lucri_leads_qualificados_sync.py)
                         0,  # LEADS FECHADOS (manual, ver lucri_leads_qualificados_sync.py)
                         safe_div(cli, imp), freq, safe_div(pv, cli), safe_div(leads, pv),
                         safe_div(spend, cli), safe_div(spend, imp)*1000, safe_div(spend, leads),
                         "",  # CPLQ
                         spend])
        gid = sheets.get_tab_gid(sheet_id, TAB_A)
        sheets.append_and_format(sheet_id, gid, TAB_A, rows,
                                 percent_cols=[13,15,16], currency_cols=[17,18,19,21])
        print(f"  CONJUNTOS: {len(rows)} linha(s)")

        existing = sheets.existing_keys(sheet_id, TAB_D)
        rows     = []
        for a in _items_for(payload["anuncios"], d):
            cname, aname, dname = a["campanha"], a["conjunto"], a["nome"]
            imp, reach, cli, plays, leads, spend = (
                a["impressoes"], a["alcance"], a["cliques"], a["plays"], a["leads"], a["gasto"])
            if imp == 0 and spend == 0: continue
            c_sid = camp_ids.get(cname)           or get_id(id_map, "campaigns", f"{kp}:{cname}", ip)
            a_sid = adset_ids.get((cname, aname)) or get_id(id_map, "adsets", f"{kp}:{cname}:{aname}", f"{c_sid}.")
            sid   = get_id(id_map, "ads", f"{kp}:{cname}:{aname}:{dname}", f"{a_sid}.")
            if (sid, date_disp) in existing:
                print(f"  [skip] anúncio {dname}"); continue
            rows.append([sid, date_in, cname, aname, dname, dname,
                         imp, reach, cli, plays, leads,
                         0,  # LEADS QUALIFICADOS (manual, ver lucri_leads_qualificados_sync.py)
                         0,  # LEADS FECHADOS (manual, ver lucri_leads_qualificados_sync.py)
                         safe_div(cli, imp), safe_div(plays, imp),
                         safe_div(spend, cli), safe_div(spend, imp)*1000, safe_div(spend, leads),
                         "",  # CPLQ
                         spend])
        gid = sheets.get_tab_gid(sheet_id, TAB_D)
        sheets.append_and_format(sheet_id, gid, TAB_D, rows,
                                 percent_cols=[13,14], currency_cols=[15,16,17,19])
        print(f"  ANÚNCIOS:  {len(rows)} linha(s)")


# ── Inserção CWB Kids (GA4 + Meta) ───────────────────────────────────────────

def process_cwbkids(payload, sheets, sheet_id, id_map, cfg, ga4):
    kp = cfg["key_prefix"]
    ip = cfg["id_prefix"]

    for d in get_dates(payload):
        date_in   = date_br_input(d)
        date_disp = date_br_display(d)
        print(f"\n=== {d.isoformat()} ===")

        ga4_data = ga4.fetch_by_campaign(d.isoformat(), "sessionManualCampaignName")
        print(f"  GA4 campanhas: {list(ga4_data.keys())}")

        existing = sheets.existing_keys(sheet_id, TAB_C)
        camp_ids = {}
        rows     = []
        for c in _items_for(payload["campanhas"], d):
            cname = c["nome"]
            imp, cli, spend = c["impressoes"], c["cliques"], c["gasto"]
            obj = normalizar_objetivo(c.get("objetivo", "VENDAS"))
            sid = get_id(id_map, "campaigns", f"{kp}:{cname}", ip)
            camp_ids[cname] = sid
            if (sid, date_disp) in existing:
                print(f"  [skip] campanha {cname}"); continue
            g    = ga4_data.get(cname, {})
            pv   = g.get("page_views",     0.0)
            atc  = g.get("add_to_cart",    0.0)
            ic   = g.get("begin_checkout", 0.0)
            comp = g.get("purchases",      0.0)
            rev  = g.get("revenue",        0.0)
            rows.append([sid, date_in, cname, "", obj,
                         imp, cli, pv, atc, ic,
                         safe_div(cli, imp),           # [10] CTR (LINK)
                         rev,                           # [11] RECEITA
                         safe_div(rev, spend),          # [12] ROAS
                         safe_div(spend, cli),          # [13] CPC (LINK)
                         safe_div(pv, cli),             # [14] CONNECT RATE
                         safe_div(comp, pv),            # [15] TAXA DE CONVERSÃO
                         "",                            # [16] CPC
                         safe_div(spend, imp)*1000,     # [17] CPM
                         safe_div(spend, comp),         # [18] CPA
                         spend] + ([comp] if getattr(sheets, "is_d1", False) else []))  # compras [20] no D1
        gid = sheets.get_tab_gid(sheet_id, TAB_C)
        sheets.append_and_format(sheet_id, gid, TAB_C, rows,
                                 percent_cols=[10, 14, 15], currency_cols=[11, 13, 17, 18, 19])
        print(f"  CAMPANHAS: {len(rows)} linha(s)")

        existing  = sheets.existing_keys(sheet_id, TAB_A)
        adset_ids = {}
        rows      = []
        for c in _items_for(payload["conjuntos"], d):
            cname, aname = c["campanha"], c["nome"]
            imp, reach, cli, freq, spend = (
                c["impressoes"], c["alcance"], c["cliques"], c.get("frequencia", 0), c["gasto"])
            c_sid = camp_ids.get(cname) or get_id(id_map, "campaigns", f"{kp}:{cname}", ip)
            sid   = get_id(id_map, "adsets", f"{kp}:{cname}:{aname}", f"{c_sid}.")
            adset_ids[(cname, aname)] = sid
            if (sid, date_disp) in existing:
                print(f"  [skip] conjunto {aname}"); continue
            rows.append([sid, date_in, cname, aname, "", audience_level(cname),
                         imp, reach, cli, "", "", "",
                         safe_div(cli, imp), freq, "",
                         safe_div(spend, cli), safe_div(spend, imp)*1000, "", spend])
        gid = sheets.get_tab_gid(sheet_id, TAB_A)
        sheets.append_and_format(sheet_id, gid, TAB_A, rows,
                                 percent_cols=[12], currency_cols=[15, 16, 18])
        print(f"  CONJUNTOS: {len(rows)} linha(s)")

        existing = sheets.existing_keys(sheet_id, TAB_D)
        rows     = []
        for a in _items_for(payload["anuncios"], d):
            cname, aname, dname = a["campanha"], a["conjunto"], a["nome"]
            imp, reach, cli, plays, spend = (
                a["impressoes"], a["alcance"], a["cliques"], a["plays"], a["gasto"])
            if imp == 0 and spend == 0: continue
            c_sid = camp_ids.get(cname)           or get_id(id_map, "campaigns", f"{kp}:{cname}", ip)
            a_sid = adset_ids.get((cname, aname)) or get_id(id_map, "adsets", f"{kp}:{cname}:{aname}", f"{c_sid}.")
            sid   = get_id(id_map, "ads", f"{kp}:{cname}:{aname}:{dname}", f"{a_sid}.")
            if (sid, date_disp) in existing:
                print(f"  [skip] anúncio {dname}"); continue
            rows.append([sid, date_in, cname, aname, dname, "",
                         imp, reach, cli, plays, "",
                         safe_div(cli, imp), "",       # [11] CTR (LINK), [12] ROAS
                         safe_div(spend, cli),          # [13] CPC (LINK)
                         safe_div(plays, imp), "",      # [14] HOOK RATE, [15] CPC
                         safe_div(spend, imp)*1000, "", spend])  # [16] CPM, [17] CPA, [18] INVEST
        gid = sheets.get_tab_gid(sheet_id, TAB_D)
        sheets.append_and_format(sheet_id, gid, TAB_D, rows,
                                 percent_cols=[11, 14], currency_cols=[13, 16, 18])
        print(f"  ANÚNCIOS:  {len(rows)} linha(s)")


def find_latest_export():
    """Procura o arquivo JSON mais recente na pasta Downloads."""
    import glob
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    # Inclui o nome atual meta_<cliente>_<data>_<periodo>.json e o legado.
    files = glob.glob(os.path.join(downloads, "meta_*.json"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def main():
    # Aceita caminho como argumento ou busca automaticamente em Downloads
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = find_latest_export()
        if not path:
            print("Nenhum arquivo meta_*.json encontrado em Downloads.")
            print("Use: python scripts/meta_from_extension.py <caminho_do_arquivo.json>")
            sys.exit(1)

    print(f"Lendo: {path}")
    raw = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                raw = f.read()
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        raise ValueError(f"Não foi possível ler '{path}' em nenhum encoding conhecido.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        sys.exit(1)

    account_id = payload.get("accountId")
    if account_id not in CLIENTES:
        print(f"Account ID '{account_id}' não mapeado em CLIENTES.")
        print("Adicione-o ao dicionário CLIENTES no topo do script.")
        sys.exit(1)

    cfg    = CLIENTES[account_id]
    print(f"Cliente: {cfg['nome']} ({account_id})")

    env      = parse_env(ENV_PATH)
    sheets   = SheetsClient(env)
    sheet_id = env[cfg["sheet_env"]]

    id_map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg["id_map_file"])
    id_map      = load_id_map(id_map_path)

    if cfg["usa_ga4"]:
        ga4 = GA4Client(env)
        process_cwbkids(payload, sheets, sheet_id, id_map, cfg, ga4)
    else:
        process_lucri(payload, sheets, sheet_id, id_map, cfg)

    sheets.sort_tabs_by_date(sheet_id, [TAB_C, TAB_A, TAB_D])
    save_id_map(id_map, id_map_path)
    print("\nConcluído.")


if __name__ == "__main__":
    main()
