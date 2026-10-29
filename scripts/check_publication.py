"""Verifica arquivos versionados sem imprimir conteúdo potencialmente secreto."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'gh[pousr]_[A-Za-z0-9_]{25,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{30,}'),
    re.compile(r'AIza[0-9A-Za-z_-]{30,}'),
    re.compile(r'\bEAA[A-Za-z0-9]{40,}'),
]


def main():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True)
    files = [name for name in result.stdout.decode('utf-8').split('\0') if name]
    failures = []
    for name in files:
        path = Path(name)
        private_name = path.name in {'.env', '.mcp.json', 'google-services.json', 'cookies.txt'}
        private_env = path.name.startswith('.env.') and path.name != '.env.example'
        private_state = path.name.endswith(('_id_map.json', '_ids.json', '_state.json'))
        if private_name or private_env or private_state or any(p in path.parts for p in ['backups', 'node_modules', '.venv']):
            failures.append(name)
            continue
        if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.ico'}:
            continue
        content = (ROOT / path).read_text(encoding='utf-8', errors='replace')
        if any(pattern.search(content) for pattern in PATTERNS):
            failures.append(name)
    if failures:
        print('Revisar arquivos: ' + ', '.join(failures))
        return 1
    print(f'Auditoria: {len(files)} arquivos versionados; nenhum padrao sensivel encontrado.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
