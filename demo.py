"""Demonstra o dashboard original com métricas sintéticas, sem credenciais."""
import argparse
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / 'CWB KIDS/dashboard'
PUBLIC = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    '/css/styles.css': ('css/styles.css', 'text/css; charset=utf-8'),
    '/js/app.js': ('js/app.js', 'text/javascript; charset=utf-8'),
    '/images/google-ads.svg': ('images/google-ads.svg', 'image/svg+xml'),
    '/images/meta_PNG5.png': ('images/meta_PNG5.png', 'image/png'),
}


def synthetic_export():
    payload = {'accountId': '1111111111111111', 'datePreset': 'last_30d',
               'campanhas': [], 'conjuntos': [], 'anuncios': []}
    for day in range(28):
        stamp = (date(2026, 10, 1) + timedelta(days=day)).isoformat()
        for index, name in enumerate(['Prospecção · Coleção Demo', 'Remarketing · Loja Demo']):
            common = {'date': stamp, 'impressoes': 3500 + day * 95 + index * 300,
                      'cliques': 105 + day * 3 + index * 12, 'gasto': round(85 + day * 2.3 + index * 12, 2),
                      'leads': 8 + day % 5, 'pv': 70 + day * 2}
            campaign = f'demo-c{index + 1}'
            adset = f'demo-j{index + 1}'
            payload['campanhas'].append(dict(common, nome=name, objetivo='OUTCOME_SALES', id=campaign))
            payload['conjuntos'].append(dict(common, campanha=name, nome='Público de demonstração',
                alcance=3000 + day * 70, frequencia=1.3, campaign_id=campaign, id=adset))
            payload['anuncios'].append(dict(common, campanha=name, conjunto='Público de demonstração',
                nome=f'Criativo Demo {index + 1}', alcance=3000 + day * 70, plays=700 + day * 20,
                campaign_id=campaign, adset_id=adset, id=f'demo-a{index + 1}'))
    return payload


def dashboard_data():
    """Usa o formato do frontend existente; nada vem de APIs ou arquivos privados."""
    data = {key: [] for key in ['metaCampanhas', 'metaConjuntos', 'metaAnuncios',
        'googleCampanhas', 'googleGrupos', 'googleTermos', 'organico', 'marketplace', 'insights']}
    export = synthetic_export()
    for index, row in enumerate(export['campanhas']):
        purchases = 4 + index % 5
        revenue = purchases * 95
        spend, clicks, impressions = row['gasto'], row['cliques'], row['impressoes']
        base = {'DATA': row['date'], 'CAMPANHA': row['nome'], 'IMPRESSÕES': impressions,
                'CLIQUES': clicks, 'COMPRAS': purchases, 'RECEITA': revenue, 'INVESTIMENTO': spend,
                'CTR (LINK)': clicks / impressions, 'CPC (LINK)': spend / clicks,
                'CPM': spend / impressions * 1000, 'CPA': spend / purchases, 'ROAS': revenue / spend,
                'PAGE VIEW': row['pv'], 'ADD TO CART': 20 + index % 8,
                'CONNECT RATE': row['pv'] / clicks, 'TAXA DE CONVERSÃO': purchases / row['pv'],
                'INITIATE CHECKOUT': 10 + index % 5, 'OBJETIVO': 'VENDAS'}
        data['metaCampanhas'].append(base)
        data['metaConjuntos'].append(dict(base, **{'CONJUNTO DE ANÚNCIO': 'Público de demonstração',
            'CLIQUES NO LINK': clicks, 'ALCANCE': impressions * .8, 'FREQUÊNCIA': 1.25}))
        data['metaAnuncios'].append(dict(base, **{'CONJUNTO DE ANÚNCIO': 'Público de demonstração',
            'ANÚNCIO': f'Criativo Demo {index % 2 + 1}', 'CLIQUES NO LINK': clicks,
            'REPRODUÇÕES DE 3 SEG': 700, 'HOOK RATE': 700 / impressions}))
        data['googleCampanhas'].append(dict(base, CAMPANHA='Pesquisa · Loja Demo',
            INVESTIMENTO=spend * .6, RECEITA=revenue * .7, COMPRAS=max(1, purchases - 2)))
    for day in range(28):
        stamp = (date(2026, 10, 1) + timedelta(days=day)).isoformat()
        data['organico'].append({'DATA': stamp, 'SESSÕES': 600 + day * 15,
            'RECEITA TOTAL DA LOJA': 4500 + day * 80, 'PEDIDOS TOTAIS DA LOJA': 40 + day})
    return data


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/data':
            body = json.dumps(dashboard_data(), ensure_ascii=False).encode('utf-8')
            mime = 'application/json; charset=utf-8'
        elif path in PUBLIC:
            filename, mime = PUBLIC[path]
            body = (DASHBOARD / filename).read_bytes()
            if filename == 'index.html':
                body = body.replace(b'<button class="topbar-logout" id="logout-btn">Sair</button>',
                                    ' <span>Ambiente de demonstração</span>'.encode('utf-8'))
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', args.port), DemoHandler) as server:
        print(f'Demo com dados fictícios: http://127.0.0.1:{args.port}', flush=True)
        print('Ctrl+C encerra. Gráficos precisam acessar o CDN do Chart.js.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
