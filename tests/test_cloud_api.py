from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from app.cloud.main import app
from app.cloud.auth import User
from app.cloud.store import SupabaseStore

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')

def test_unconfigured_fails_closed(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_ANON_KEY', raising=False)
    with TestClient(app) as c:
        assert c.get('/api/health').status_code == 200
        assert c.get('/api/config').json()['configured'] is False
        assert c.get('/api/profile').status_code == 503

def test_protected_endpoints(configured):
    with TestClient(app) as c:
        for path in ['/api/profile', '/api/jobs', '/api/metrics', '/api/resumes']:
            assert c.get(path).status_code == 401

def test_auth_validated_each_request_and_owner_filter(configured, monkeypatch):
    owner = str(uuid4())
    requests = []
    def handler(request):
        requests.append(request)
        assert request.headers['apikey'] == 'public-anon'
        assert request.headers['authorization'] == 'Bearer valid'
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': owner, 'email': 'x@example.com'})
        assert request.url.params['user_id'] == 'eq.' + owner
        return httpx.Response(200, json=[])
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    with TestClient(app) as c:
        for _ in range(2):
            assert c.get('/api/jobs', headers={'Authorization': 'Bearer valid', 'X-User-Id': str(uuid4())}).status_code == 200
    assert sum(r.url.path == '/auth/v1/user' for r in requests) == 2

def test_invalid_token_is_sanitized(configured, monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(lambda req: httpx.Response(401, json={'secret': 'do-not-leak'})), **kwargs))
    with TestClient(app) as c:
        response = c.get('/api/profile', headers={'Authorization': 'Bearer private-token'})
        assert response.status_code == 401
        assert 'private-token' not in response.text
        assert 'do-not-leak' not in response.text

def test_validation_redacts_supplied_owner(configured, monkeypatch):
    from app.cloud.auth import require_user
    app.dependency_overrides[require_user] = lambda: User(str(uuid4()), None, 'token')
    try:
        with TestClient(app) as c:
            response = c.post('/api/jobs', json={'title': 'Engineer', 'user_id': 'private-secret'})
            assert response.status_code == 422
            assert 'private-secret' not in response.text
            assert 'input' not in response.json()['detail'][0]
    finally:
        app.dependency_overrides.clear()

def test_foreign_job_not_found(configured, monkeypatch):
    owner, foreign_job = str(uuid4()), str(uuid4())
    original = httpx.AsyncClient
    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': owner})
        assert request.url.params['user_id'] == 'eq.' + owner
        assert request.url.params['id'] == 'eq.' + foreign_job
        return httpx.Response(200, json=[])
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    with TestClient(app) as c:
        response = c.get('/api/jobs/' + foreign_job, headers={'Authorization': 'Bearer valid'})
        assert response.status_code == 404

def test_resume_rejects_invalid_file_without_storage(configured):
    from app.cloud.auth import require_user
    app.dependency_overrides[require_user] = lambda: User(str(uuid4()), None, 'token')
    try:
        with TestClient(app) as c:
            assert c.post('/api/resumes', files={'file': ('resume.exe', b'123')}).status_code == 400
            assert c.post('/api/resumes', files={'file': ('resume.pdf', b'x' * (5 * 1024 * 1024 + 1))}).status_code == 413
    finally:
        app.dependency_overrides.clear()

@pytest.mark.parametrize('key', ['sb_secret_accidental', 'eyJhbGciOiJub25lIn0.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.signature'])
def test_privileged_config_redacted(configured, monkeypatch, key):
    monkeypatch.setenv('SUPABASE_ANON_KEY', key)
    with TestClient(app) as c:
        payload = c.get('/api/config').json()
        assert payload['configured'] is False
        assert payload['supabase_anon_key'] == ''
        assert key not in c.get('/api/config').text
        assert c.get('/api/jobs', headers={'Authorization': 'Bearer token'}).status_code == 503

def test_allowed_origins_alias_and_url_restriction(configured, monkeypatch):
    from app.cloud.config import settings
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    monkeypatch.setenv('ALLOWED_ORIGINS', 'https://career.example,*')
    assert settings().cors_origins == ('https://career.example',)
    monkeypatch.setenv('SUPABASE_URL', 'https://attacker.example')
    assert settings().configured is False

@pytest.fixture
def fake_authenticated_store():
    class MemoryStore:
        def __init__(self):
            self.data = {}
            self.records = {}
        async def profile(self): return self.data
        async def save_profile(self, data):
            self.data = data
            return data
        async def jobs(self): return list(self.records.values())
        async def create_job(self, data):
            row = {**data, 'id': str(uuid4())}
            self.records[row['id']] = row
            return row
        async def job(self, id): return self.records[str(id)]
        async def update_job(self, id, data):
            self.records[str(id)].update(data)
            return self.records[str(id)]
        async def delete_job(self, id): del self.records[str(id)]
    from app.cloud.store import get_store
    store = MemoryStore()
    app.dependency_overrides[get_store] = lambda: store
    try:
        yield store
    finally:
        app.dependency_overrides.clear()

def test_profile_job_crud_and_analysis(configured, fake_authenticated_store):
    with TestClient(app) as c:
        response = c.put('/api/profile', json={'full_name': 'Python Name', 'skills': ['sql'], 'term': 2})
        assert response.status_code == 200
        assert c.get('/api/profile').json()['skills'] == ['sql']
        created = c.post('/api/jobs', json={'title': 'Python SQL', 'description': 'Python SQL developer', 'url': 'https://jobs.example/123'}).json()
        jid = created['id']
        assert c.get('/api/jobs/' + jid).json()['title'] == 'Python SQL'
        result = c.post('/api/jobs/' + jid + '/analyze').json()
        assert result['analysis']['matched_skills'] == ['sql']
        assert 'python' in result['analysis']['missing_skills']
        assert c.patch('/api/jobs/' + jid, json={'status': 'applied'}).json()['status'] == 'applied'
        assert len(c.get('/api/jobs').json()) == 1
        assert c.delete('/api/jobs/' + jid).status_code == 204
        assert c.get('/api/jobs').json() == []

@pytest.mark.parametrize('data', [{'title': 'Test', 'status': 'invented'}, {'title': 'Test', 'url': 'javascript:alert(1)'}, {'title': 'Test', 'url': 'https://user:secret@jobs.example'}, {'title': 'Test', 'user_id': 'other-owner'}])
def test_job_rejects_unsafe_fields(configured, fake_authenticated_store, data):
    with TestClient(app) as c:
        assert c.post('/api/jobs', json=data).status_code == 422
    assert fake_authenticated_store.records == {}

@pytest.mark.parametrize('data', [{'skills': 'python'}, {'skills': [42]}, {'user_id': 'other-owner'}, {'summary': 'x' * 10001}, {'evidence': [{'fact': {'nested': 'unbounded'}}]}])
def test_profile_rejects_untyped_or_unbounded_fields(configured, fake_authenticated_store, data):
    with TestClient(app) as c:
        assert c.put('/api/profile', json=data).status_code == 422
    assert fake_authenticated_store.data == {}
