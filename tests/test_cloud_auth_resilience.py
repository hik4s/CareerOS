from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.cloud.main import app


@pytest.fixture
def auth_server(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    original = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(
            transport=httpx.MockTransport(handler), **kwargs))
    return install


@pytest.mark.parametrize('status', [429, 500, 502, 503])
def test_auth_outage_is_not_reported_as_expired_session(auth_server, status):
    calls = []
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(status, json={'message': 'private upstream details'})
    auth_server(handler)
    with TestClient(app) as client:
        response = client.get('/api/profile', headers={'Authorization': 'Bearer private-token'})
    assert response.status_code == 503
    assert response.headers['Retry-After'] == '30'
    assert calls == ['/auth/v1/user']
    assert 'private-token' not in response.text
    assert 'private upstream details' not in response.text


def test_auth_network_failure_is_temporary(auth_server):
    def handler(request):
        raise httpx.ConnectError('private transport details', request=request)
    auth_server(handler)
    with TestClient(app) as client:
        response = client.get('/api/jobs', headers={'Authorization': 'Bearer token'})
    assert response.status_code == 503
    assert 'private transport details' not in response.text


@pytest.mark.parametrize('payload', [[], None, {'id': None}, {'id': 'invalid'}])
def test_malformed_auth_response_fails_closed_without_server_crash(auth_server, payload):
    auth_server(lambda request: httpx.Response(200, json=payload))
    with TestClient(app) as client:
        response = client.get('/api/profile', headers={'Authorization': 'Bearer token'})
    assert response.status_code == 503


def test_personal_api_success_and_failure_are_not_cacheable(auth_server):
    owner = str(uuid4())
    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': owner})
        return httpx.Response(200, json=[])
    auth_server(handler)
    with TestClient(app) as client:
        responses = [client.get('/api/jobs', headers={'Authorization': 'Bearer token'}),
                     client.get('/api/profile')]
    assert [r.status_code for r in responses] == [200, 401]
    for response in responses:
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.headers['Referrer-Policy'] == 'no-referrer'
        assert response.headers['X-Content-Type-Options'] == 'nosniff'


def test_unexpected_api_error_is_sanitized_and_not_cacheable():
    from app.cloud.store import get_store
    def broken_store():
        raise RuntimeError('private internal details')
    app.dependency_overrides[get_store] = broken_store
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get('/api/profile')
        assert response.status_code == 500
        assert 'private internal details' not in response.text
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.headers['Referrer-Policy'] == 'no-referrer'
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
    finally:
        app.dependency_overrides.clear()
