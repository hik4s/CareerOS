from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from app.cloud import discovery
from app.cloud.auth import User, require_user
from app.cloud.main import app


def test_discovery_requires_a_session(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    with TestClient(app) as client:
        assert client.get('/api/discovery/jobs').status_code == 401


def test_discovery_filters_deduplicates_and_reports_outage(monkeypatch):
    row = discovery.normalize({
        'title': 'Estágio em Python', 'company_name': 'Empresa',
        'location': 'São Paulo', 'remote': True,
        'url': 'https://example.com/jobs/1',
    }, 'Arbeitnow', '')

    async def feed(key):
        if key == 'brex':
            return [], False
        return [row, row, {**row, 'url': 'https://example.com/jobs/2', 'remote': False}], True

    monkeypatch.setattr(discovery, 'get_feed', feed)
    app.dependency_overrides[require_user] = lambda: User('owner', None, 'token')
    try:
        with TestClient(app) as client:
            response = client.get('/api/discovery/jobs', params={
                'q': 'estagio PYTHON', 'location': 'sao paulo', 'remote': True,
            })
        assert response.status_code == 200
        result = response.json()
        assert result['total'] == 1
        assert result['jobs'][0]['url'] == 'https://example.com/jobs/1'
        assert {'name': 'Brex', 'available': False} in result['sources']
        linkedin = next(item for item in result['portals'] if item['name'] == 'LinkedIn')
        assert parse_qs(urlsplit(linkedin['url']).query)['f_WT'] == ['2']
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_feed_rejects_unsafe_or_missing_urls():
    for url in ('javascript:alert(1)', 'https://user@example.com/path', None):
        assert discovery.normalize({'title': 'Vaga', 'url': url}, 'Arbeitnow', '') is None
