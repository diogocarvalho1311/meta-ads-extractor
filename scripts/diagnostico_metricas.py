"""Diagnostico somente leitura dos dois bancos de metricas."""
from pathlib import Path
from cwbkids_commons import parse_env
from cloudflare_rest import Cloudflare
from d1_metricas import SCHEMA,d1_enabled
ROOT=Path(__file__).resolve().parents[1]
def main():
    env=parse_env(ROOT/'.env')
    print('Destino ativo:', 'Cloudflare D1' if d1_enabled(env) else 'Google Sheets',flush=True)
    api=Cloudflare(env)
    for client,tabs in SCHEMA.items():
        db=env['D1_DATABASE_ID_'+client.upper()]
        print('\n'+client.upper(),flush=True)
        for spec in tabs.values():
            r=api.query(db,f'SELECT COUNT(*) AS total,MAX(data) AS ultima_data FROM {spec["table"]}')[0]
            print(f'  {spec["table"]}: {r["total"]} registros; ultima data: {r["ultima_data"]}',flush=True)
if __name__=='__main__':main()
