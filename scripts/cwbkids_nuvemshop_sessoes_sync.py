"""
Importa CSV exportado da Nuvemshop para a aba NUVEMSHOP.

Detecta automaticamente o tipo pelo cabeçalho:
  - "Visitas" → coluna D (SESSÕES)
  - "Vendas"  → coluna B (PEDIDOS TOTAIS DA LOJA)

Uso:
    python cwbkids_nuvemshop_sessoes_sync.py <arquivo.csv>
"""
import csv
import os
import sys
from datetime import date, timedelta
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cwbkids_commons import SheetsClient, parse_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

TAB = "NUVEMSHOP"
SHEETS_EPOCH = date(1899, 12, 30)

# Mapeamento: coluna do CSV → coluna da planilha (letra) e nome legível
METRIC_MAP = {
    "Visitas":                ("D", "SESSÕES"),
    "Vendas":                 ("B", "PEDIDOS TOTAIS DA LOJA"),
    "Quantidade de vendas":   ("B", "PEDIDOS TOTAIS DA LOJA"),
    "Visitas únicas":         ("D", "SESSÕES"),
}


def serial_to_date(n):
    return SHEETS_EPOCH + timedelta(days=int(float(n)))


def main():
    if len(sys.argv) < 2:
        print("Uso: python cwbkids_nuvemshop_sessoes_sync.py <arquivo.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]

    # Lê CSV e detecta tipo pelo cabeçalho
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        metric_col = next((k for k in METRIC_MAP if k in fieldnames), None)
        if not metric_col:
            print(f"❌ Cabeçalho não reconhecido: {fieldnames}")
            print(f"   Esperado: {list(METRIC_MAP.keys())}")
            sys.exit(1)

        sheet_col, col_name = METRIC_MAP[metric_col]
        dados = {}
        for row in reader:
            try:
                d = date.fromisoformat(row["Data"].strip())
                v = int(row[metric_col].strip())
                dados[d] = v
            except (KeyError, ValueError):
                continue

    print(f"CSV: {len(dados)} dia(s) de {metric_col} → coluna {sheet_col} ({col_name})")
    if not dados:
        print("Nenhum dado encontrado no CSV.")
        return

    env = parse_env(ENV_PATH)
    sheets = SheetsClient(env)
    sheet_id = env["SHEETS_ID_CWBKIDS_METRICAS"]

    # Lê coluna A como serial numbers para mapear data → número da linha
    rows_a = sheets.values_get(sheet_id, f"{TAB}!A2:A10000",
                               value_render_option="UNFORMATTED_VALUE").get("values", [])

    date_to_row = {}
    for i, row in enumerate(rows_a):
        if row:
            try:
                date_to_row[serial_to_date(row[0])] = i + 2
            except (ValueError, TypeError):
                pass

    print(f"Linhas na planilha: {len(date_to_row)}")

    is_vendas = sheet_col == "B"  # PEDIDOS TOTAIS DA LOJA

    updates = []
    sem_linha = []
    for d, valor in sorted(dados.items()):
        if d not in date_to_row:
            sem_linha.append(d.isoformat())
            continue
        row_num = date_to_row[d]
        updates.append({"range": f"{TAB}!{sheet_col}{row_num}", "values": [[valor]]})
        # Quando vendas = 0, zera também RECEITA TOTAL DA LOJA (col C)
        if is_vendas and valor == 0:
            updates.append({"range": f"{TAB}!C{row_num}", "values": [[0]]})
            print(f"  {d.isoformat()} → {valor} (receita → 0)")
        else:
            print(f"  {d.isoformat()} → {valor}")

    if sem_linha:
        print(f"\n⚠ Datas sem linha na planilha:")
        for s in sem_linha:
            print(f"  {s}")

    if updates:
        sheets.values_batch_update(sheet_id, updates, value_input_option="RAW")
        print(f"\n{len(updates)} linha(s) atualizada(s) em {col_name}.")
    else:
        print("\nNenhuma linha atualizada.")


if __name__ == "__main__":
    main()
