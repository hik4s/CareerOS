"""Reproducible UI screenshots with synthetic fixtures, never a real account.

Run from repository root: python scripts/capture_portfolio.py
Requires Playwright and its Chromium browser. No application code is modified.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'app/cloud/static'
OUTPUT = ROOT / 'docs/assets'
PROFILE = {'full_name': 'Pessoa de Demonstração', 'headline': 'Desenvolvimento Python',
           'skills': ['Python', 'SQL', 'FastAPI'], 'city': 'Cidade fictícia',
           'education': 'Tecnologia da Informação — exemplo fictício', 'term': 2}
JOBS = [dict(id=f'00000000-0000-4000-8000-{i:012d}', title=title,
             company=company, location='Remoto · Brasil', work_model='Remoto',
             status=status, description='Oportunidade fictícia para demonstrar a organização de candidaturas. Python, SQL e APIs REST.',
             url=f'https://example.com/vagas/{i}', created_at='2026-11-01T12:00:00Z',
             updated_at='2026-11-03T12:00:00Z')
        for i, (title, company, status) in enumerate([
            ('Desenvolvedor Python Júnior', 'Empresa Exemplo A', 'saved'),
            ('Desenvolvedor Backend Júnior', 'Empresa Exemplo B', 'applied'),
            ('Analista de Automação Júnior', 'Empresa Exemplo C', 'interview')], 1)]

# Adapter implements only calls made while rendering these read-only UI views.
# It is served instead of the SDK ONLY by this isolated screenshot fixture server.
SDK = '''window.supabase={createClient:()=>({auth:{
getSession:async()=>({data:{session:{access_token:'synthetic-demo-token',
user:{id:'00000000-0000-4000-8000-000000000000',email:'demo@example.com',
user_metadata:{full_name:'Pessoa de Demonstração'}}}},error:null}),
onAuthStateChange:()=>({data:{subscription:{unsubscribe(){}}}})
}})};'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        fixtures = {'/api/config': {'configured': True, 'supabase_url': 'http://127.0.0.1',
                                   'supabase_anon_key': 'synthetic-demo-key'},
                    '/api/profile': PROFILE, '/api/jobs': JOBS, '/api/resumes': [],
                    '/api/ai/history': [], '/api/auth/providers': {'providers': []}}
        if path in fixtures:
            data, kind = json.dumps(fixtures[path], ensure_ascii=False).encode(), 'application/json'
        elif path == '/static/vendor/supabase.js':
            data, kind = SDK.encode(), 'application/javascript'
        elif path.startswith('/static/'):
            file = (STATIC / path.removeprefix('/static/')).resolve()
            if not file.is_relative_to(STATIC.resolve()) or not file.is_file():
                self.send_error(404)
                return
            import mimetypes
            data, kind = file.read_bytes(), mimetypes.guess_type(file)[0] or 'application/octet-stream'
        elif path in ('/', '/auth'):
            html = (STATIC / 'index.html').read_text(encoding='utf-8')
            banner = '<div style="position:relative;background:#fff0bd;color:#342600;text-align:center;padding:8px;font:13px system-ui">DEMONSTRAÇÃO LOCAL · DADOS FICTÍCIOS · AUTENTICAÇÃO E API SIMULADAS</div>'
            data, kind = html.replace('<body>', '<body>' + banner).encode(), 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def capture():
    from playwright.sync_api import sync_playwright
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                context = browser.new_context(viewport={'width': 1440, 'height': 1050},
                                              reduced_motion='reduce')
                context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') else route.abort())
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(origin)
                page.locator('#shell').wait_for(state='visible')
                page.locator('#auth-transition.hidden').wait_for(state='attached')
                page.get_by_text('Pessoa de Demonstração', exact=True).first.wait_for()
                page.get_by_text('Desenvolvedor Python Júnior', exact=True).first.wait_for()
                page.screenshot(path=str(OUTPUT / 'portfolio-overview.png'), full_page=True)
                page.get_by_role('link', name='Minhas vagas', exact=False).click()
                page.get_by_role('heading', name='Minhas vagas', exact=True).wait_for()
                page.get_by_text('Desenvolvedor Python Júnior', exact=True).first.wait_for()
                page.screenshot(path=str(OUTPUT / 'portfolio-jobs.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(OUTPUT / 'portfolio-jobs-mobile.png'), full_page=True)
                if errors:
                    raise RuntimeError('\n'.join(errors))
                print('3 capturas geradas; interface original, fixtures sintéticas, sem erros JavaScript.')
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    capture()
