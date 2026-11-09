import os
import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
html = re.sub(r'<script\b[^>]*>.*?</script>', '', (root/'app/cloud/static/index.html').read_text(encoding='utf-8'), flags=re.S)
source = (root/'app/cloud/static/app.js').read_text(encoding='utf-8')
start = source.index('(async () => {')
end = source.index('\n})();', start) + len('\n})();')
source = source[:start] + source[end:]
saved = []
suggestions = {'full_name':'Ana Souza', 'email':'ana@example.com', 'skills':['Python','PostgreSQL'], 'summary':'Automação com <Python>.'}

def route_request(route):
    request = route.request
    path = request.url.split('careeros.test')[-1].split('?')[0]
    if path == '/':
        route.fulfill(body=html, content_type='text/html')
    elif path.startswith('/static/'):
        file = root/'app/cloud'/path.lstrip('/')
        route.fulfill(body=file.read_text(encoding='utf-8'), content_type='text/css')
    elif path == '/api/resumes' and request.method == 'POST':
        assert 'multipart/form-data' in request.headers['content-type']
        route.fulfill(json={'id':'resume-demo','filename':'resume.docx'})
    elif path.endswith('/profile-preview'):
        route.fulfill(json={'has_text':True,'suggestions':suggestions})
    elif path == '/api/profile' and request.method == 'PUT':
        saved.append(request.post_data_json)
        route.fulfill(json=saved[-1])
    elif path == '/api/profile':
        route.fulfill(json=saved[-1] if saved else {})
    else:
        route.fulfill(json=[])

with sync_playwright() as p:
    browser = p.chromium.launch(channel=os.environ.get('CAREEROS_TEST_BROWSER_CHANNEL', 'msedge' if sys.platform == 'win32' else 'chromium'), headless=True)
    page = browser.new_page(viewport={'width':390,'height':844})
    page.route('https://careeros.test/**', route_request)
    page.route('https://fonts.googleapis.com/**', lambda route: route.abort())
    page.goto('https://careeros.test/')
    page.add_script_tag(content=source)
    page.evaluate("""() => {
      session={user:{id:'owner'},access_token:'fake'};
      client={auth:{getSession:async()=>({data:{session}})}};
      profile={full_name:'Nome existente',email:'existente@example.com',term:4};
      resumes=[];tab='profile';workspaceReady=true;
      $('shell').classList.remove('hidden');$('auth-transition').classList.add('hidden');
      renderProfile();
    }""")
    page.locator('#profileImportFile').set_input_files({'name':'resume.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':b'synthetic file'})
    page.get_by_role('button', name='Importar currículo', exact=True).click()
    expect(page.locator('#applyProfileImport')).to_be_visible()
    expect(page.locator('[data-profile-import="full_name"]')).not_to_be_checked()
    expect(page.locator('[data-profile-import="skills"]')).to_be_checked()
    assert not saved
    page.locator('[name="summary"]').fill('Resumo revisado enquanto a prévia estava aberta.')
    expect(page.locator('[data-profile-import="summary"]')).not_to_be_checked()
    page.locator('[data-profile-import="full_name"]').check()
    page.locator('#applyProfileImport').click()
    expect(page.locator('[name="full_name"]')).to_have_value('Ana Souza')
    expect(page.locator('[name="email"]')).to_have_value('existente@example.com')
    expect(page.locator('[name="skills"]')).to_have_value('Python, PostgreSQL')
    assert not saved
    page.get_by_role('button', name='Salvar perfil', exact=True).click()
    expect(page.locator('#toast')).to_contain_text('Perfil salvo')
    assert saved[0]['full_name'] == 'Ana Souza'
    assert saved[0]['email'] == 'existente@example.com'
    assert saved[0]['summary'] == 'Resumo revisado enquanto a prévia estava aberta.'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'

    # A pending preview from a previous account must not enter the next account's form.
    page.evaluate("""() => {
      resumes=[{id:'old',filename:'old.docx'}];renderProfile();
      api=()=>new Promise(resolve=>window.finishOldPreview=resolve);
    }""")
    page.get_by_role('button', name='Usar este currículo', exact=True).click()
    page.evaluate("""() => {
      session={user:{id:'new-owner'}};profile={full_name:'Outra conta',term:2};resumes=[];
      renderProfile();window.finishOldPreview({has_text:true,suggestions:{full_name:'Vazamento'}});
    }""")
    expect(page.locator('#profileImportPreview')).to_be_empty()
    expect(page.locator('[name="full_name"]')).to_have_value('Outra conta')
    browser.close()
print('PASS Edge mobile: import, review, preservation, explicit save, no overflow, stale account response ignored')
