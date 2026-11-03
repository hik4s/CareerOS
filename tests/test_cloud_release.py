import httpx
from fastapi.testclient import TestClient
from app.cloud.main import app


def test_release_version():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['version'] == '1.1.1'


def test_detects_enabled_oauth_without_exposing_settings(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    original = httpx.AsyncClient
    def handler(request):
        assert request.url.path == '/auth/v1/settings'
        return httpx.Response(200, json={'external': {'google': True, 'github': False}, 'other': 'private-marker'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    with TestClient(app) as client:
        response = client.get('/api/auth/providers')
        assert response.json()['providers'] == ['google']
        assert response.json()['ready'] is True
        assert 'private-marker' not in response.text


def test_missing_providers_are_reported(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(200,json={'external':{}})),**kwargs))
    with TestClient(app) as client:
        assert client.get('/api/auth/providers').json()['reason'] == 'oauth_setup_required'
