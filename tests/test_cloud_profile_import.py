from io import BytesIO
from uuid import uuid4

from docx import Document
from fastapi.testclient import TestClient

from app.cloud.main import app
from app.cloud.store import get_store
from app.cloud.resume_parser import extract


def test_resume_suggestions_extract_explicit_facts_without_inventing_missing_fields():
    from app.cloud.profile_import import profile_suggestions
    document = Document()
    for line in ['CURRÍCULO', 'Ana Souza', 'ana@example.com', '+55 (18) 99999-1234',
                 'Cidade: Presidente Prudente - SP', 'linkedin.com/in/ana-souza',
                 'github.com/ana-souza', 'Formação', 'Bacharelado em Tecnologia da Informação',
                 '2º semestre', 'Previsão de conclusão: 12/2028', 'Objetivo',
                 'Estágio em desenvolvimento', 'Resumo', 'Desenvolvi automações com Python.',
                 'Habilidades', 'Python, PostgreSQL, JavaScript, React, Kotlin']:
        document.add_paragraph(line)
    stream = BytesIO()
    document.save(stream)
    result = profile_suggestions(extract(stream.getvalue(), '.docx'))
    assert result == {
        'full_name': 'Ana Souza', 'email': 'ana@example.com', 'phone': '+55 (18) 99999-1234',
        'city': 'Presidente Prudente - SP', 'linkedin': 'https://linkedin.com/in/ana-souza',
        'github': 'https://github.com/ana-souza', 'course': 'Bacharelado em Tecnologia da Informação',
        'term': 2, 'graduation_date': '12/2028', 'target_roles': ['Estágio em desenvolvimento'],
        'summary': 'Desenvolvi automações com Python.',
        'skills': ['Python', 'PostgreSQL', 'JavaScript', 'React', 'Kotlin'],
    }
    assert profile_suggestions('') == {}
    assert profile_suggestions('Currículo\nExperiência profissional\nProjetos pessoais') == {}


def test_resume_suggestions_do_not_confuse_javascript_with_java_or_invent_a_term():
    from app.cloud.profile_import import profile_suggestions
    result = profile_suggestions('Habilidades: JavaScript, React, Next.js\nExperiência: 2024 - 2026')
    assert result['skills'] == ['JavaScript', 'React', 'Next.js']
    assert 'term' not in result
    assert 'full_name' not in result
    assert 'course' not in result


def test_resume_does_not_treat_locations_or_degree_names_as_person_names():
    from app.cloud.profile_import import profile_suggestions
    for heading in ['São Paulo', 'Ciência da Computação', 'Ensino Médio Completo', 'Software Engineer']:
        assert 'full_name' not in profile_suggestions('CURRÍCULO\n' + heading + '\nana@example.com')


def test_profile_preview_is_read_only_and_only_accepts_an_owned_resume():
    owner_resume = str(uuid4())
    class Store:
        async def rows(self, table, **params):
            return [{'text': 'Nome: Ana Souza\nHabilidades: Python, SQL'}] if params['id'] == 'eq.' + owner_resume else []
        async def save_profile(self, data):
            raise AssertionError('Preview must not save a profile')
    app.dependency_overrides[get_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            response = client.get(f'/api/resumes/{owner_resume}/profile-preview')
            assert response.status_code == 200
            assert response.json() == {'has_text': True, 'suggestions': {'full_name': 'Ana Souza', 'skills': ['Python', 'SQL']}}
            assert client.get(f'/api/resumes/{uuid4()}/profile-preview').status_code == 404
    finally:
        app.dependency_overrides.pop(get_store, None)


def test_profile_preview_requires_authentication(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    with TestClient(app) as client:
        assert client.get(f'/api/resumes/{uuid4()}/profile-preview').status_code == 401


def test_docx_upload_can_fill_profile_after_explicit_review():
    from types import SimpleNamespace
    class Store:
        user = SimpleNamespace(id='owner')
        data = {}
        async def rows(self, table, **params):
            return [self.data] if self.data and params.get('id') == 'eq.' + self.data['id'] else []
        async def request(self, *args, **kwargs): return {}
        async def insert(self, table, data):
            self.data = data
            return data
    store = Store()
    app.dependency_overrides[get_store] = lambda: store
    document = Document()
    document.add_paragraph('Nome: João Souza')
    document.add_paragraph('Habilidades: Python, Comunicação')
    stream = BytesIO()
    document.save(stream)
    try:
        with TestClient(app) as client:
            uploaded = client.post('/api/resumes', files={'file': ('cv.docx', stream.getvalue())})
            assert uploaded.status_code == 201
            preview = client.get('/api/resumes/' + uploaded.json()['id'] + '/profile-preview')
            assert preview.json()['suggestions'] == {'full_name': 'João Souza', 'skills': ['Python', 'Comunicação']}
    finally:
        app.dependency_overrides.pop(get_store, None)
