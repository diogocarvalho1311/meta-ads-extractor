"""
Sincroniza Google Ads de Lucri e CWB Kids para a planilha de métricas.

CWB Kids usa GA4 (sessionGoogleAdsCampaignName) para dados de funil;
Lucri usa metrics.conversions diretamente (sem GA4).

Uso:
    python sync_google_ads.py                        # ontem
    python sync_google_ads.py 2026-08-28             # dia específico
    python sync_google_ads.py 2026-08-28 2026-08-30  # intervalo
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

SCRIPTS = [
    "lucri_google_ads_sheet_sync.py",
    "cwbkids_google_ads_sheet_sync.py",
]


def run(script, args):
    cmd = [sys.executable, str(HERE / script)] + args
    result = subprocess.run(cmd, cwd=str(HERE))
    return result.returncode


def main():
    args = sys.argv[1:]  # repassa os argumentos de data para cada script

    failed = False
    for script in SCRIPTS:
        label = script.replace("_google_ads_sheet_sync.py", "").replace("lucri", "Lucri").replace("cwbkids", "CWB Kids")
        print(f"\n{'='*40}")
        print(f"  {label}")
        print(f"{'='*40}")
        code = run(script, args)
        if code != 0:
            failed = True
            print(f"  [ERRO] {script} encerrou com código {code}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
