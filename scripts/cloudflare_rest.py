"""Acesso REST ao D1; usa token do .env ou a sessao OAuth local do Wrangler."""
import json
import os
import shutil
import subprocess
import tempfile
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]

class Cloudflare:
    def __init__(self, env):
        self.env = env
        self.account_id = env['CLOUDFLARE_ACCOUNT_ID']
        self.base = 'https://api.cloudflare.com/client/v4/accounts/' + self.account_id
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'trafego-metricas/1.0'
        self._authenticate()

    def _authenticate(self):
        token = os.environ.get('CLOUDFLARE_API_TOKEN') or self.env.get('CLOUDFLARE_API_TOKEN')
        if not token:
            roots = [Path(os.environ.get('APPDATA', Path.home())) / 'xdg.config/.wrangler/config/default.toml', Path.home()/'.config/.wrangler/config/default.toml']
            config = next((p for p in roots if p.exists()), None)
            if config is None:
                raise RuntimeError('Configure CLOUDFLARE_API_TOKEN ou execute npx wrangler login no terminal.')
            data = tomllib.loads(config.read_text(encoding='utf-8'))
            expiry = datetime.fromisoformat(data['expiration_time'].replace('Z','+00:00'))
            if expiry.timestamp() < time.time() + 120:
                command = shutil.which('npx.cmd') or shutil.which('npx')
                if command is None: raise RuntimeError('Instale Node.js ou configure CLOUDFLARE_API_TOKEN.')
                # Pasta temporaria evita falhas do npm na unidade virtual do Drive.
                result = subprocess.run([command,'--yes','wrangler@4','whoami','--json'],cwd=tempfile.gettempdir(),capture_output=True,text=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode: raise RuntimeError('Sessao Cloudflare expirada. Execute npx wrangler login no terminal.')
                data = tomllib.loads(config.read_text(encoding='utf-8'))
            token = data['oauth_token']
        self.session.headers['Authorization'] = 'Bearer ' + token

    def request(self, method, route, **kwargs):
        for attempt in range(8):
            try:
                response = self.session.request(method,self.base+route,timeout=120,**kwargs)
            except (requests.ConnectionError,requests.Timeout):
                if attempt == 7: raise RuntimeError('Cloudflare indisponivel; nenhuma troca automatica para Sheets foi feita.') from None
                time.sleep(2**attempt); continue
            if response.status_code in (429,500,502,503,504):
                if attempt < 7:
                    if response.status_code == 429:
                        try:
                            errors = response.json().get('errors', [])
                            daily = any('daily' in str(e.get('message', '')).lower() for e in errors)
                        except ValueError:
                            daily = False
                        if daily: raise RuntimeError('Cota diaria D1 atingida; aguarde a renovacao da cota. Os dados ja gravados foram preservados.')
                    wait = min(60, float(response.headers.get('Retry-After', min(60, 5*2**attempt))))
                    if response.status_code == 429: print(f'Cloudflare limitou as requisicoes; tentando novamente em {wait:.0f}s.', flush=True)
                    time.sleep(wait)
                    continue
            try: data = response.json()
            except ValueError: raise RuntimeError(f'Cloudflare retornou HTTP {response.status_code}, resposta invalida.') from None
            if not response.ok or not data.get('success'):
                # Nao imprime corpo: erros SQL podem conter dados privados.
                codes = [e.get('code') for e in data.get('errors',[])]
                raise RuntimeError(f'Cloudflare HTTP {response.status_code}, codigos {codes}. Consulte acesso e esquema D1.')
            return data['result']
        raise RuntimeError('Cloudflare excedeu o limite de tentativas.')

    def query(self, database_id, sql, params=()):
        return self.request('POST',f'/d1/database/{database_id}/query',json={'sql':sql,'params':list(params)})[0].get('results',[])

    def batch(self, database_id, statements):
        if not statements: return []
        result = self.request('POST',f'/d1/database/{database_id}/query',json={'batch':statements})
        if any(not r.get('success',True) for r in result): raise RuntimeError('Falha em lote D1.')
        return result
