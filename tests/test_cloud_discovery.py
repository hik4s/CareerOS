from fastapi.testclient import TestClient
import httpx

from app.cloud import discovery
from app.cloud.auth import User, require_user
from app.cloud.main import app
from app.cloud.store import get_store


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
        assert result['portals'] == []
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_feed_rejects_unsafe_or_missing_urls():
    for url in ('javascript:alert(1)', 'https://user@example.com/path', None):
        assert discovery.normalize({'title': 'Vaga', 'url': url}, 'Arbeitnow', '') is None


def test_greenhouse_description_preserves_readable_paragraphs():
    job = discovery.normalize({
        'title': 'Estágio',
        'absolute_url': 'https://example.com/jobs/1',
        'content': '&lt;p&gt;Aprenda Python.&lt;/p&gt;&lt;p&gt;Trabalhe em equipe.&lt;/p&gt;',
    }, 'Greenhouse', 'Empresa')
    assert job['description'].splitlines() == ['Aprenda Python.', 'Trabalhe em equipe.']


def test_search_matches_description_and_paginates(monkeypatch):
    rows = [
        discovery.normalize({
            'title': f'Vaga {index}', 'description': 'Conhecimento em análise de dados',
            'url': f'https://example.com/jobs/{index}',
        }, 'Arbeitnow', '')
        for index in range(21)
    ]

    async def feed(key):
        return (rows if key == 'arbeitnow' else []), True

    monkeypatch.setattr(discovery, 'get_feed', feed)
    app.dependency_overrides[require_user] = lambda: User('owner', None, 'token')
    try:
        with TestClient(app) as client:
            result = client.get('/api/discovery/jobs?q=analise&page=2').json()
        assert result['total'] == 21
        assert result['page'] == 2
        assert [job['title'] for job in result['jobs']] == ['Vaga 20']
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_jooble_is_merged_into_search_and_cached(monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={'jobs': [{
            'title': 'Pessoa desenvolvedora', 'company': 'Empresa',
            'location': 'São Paulo', 'snippet': '<p>Experiência em Python</p>',
            'link': 'https://br.jooble.org/jdp/123',
        }]})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(discovery.httpx, 'AsyncClient', lambda **options:
                        client_class(transport=httpx.MockTransport(respond), **options))
    monkeypatch.setenv('CAREEROS_JOOBLE_BR_API_KEY', 'test-key')

    async def feed(key):
        return [], True

    monkeypatch.setattr(discovery, 'get_feed', feed)
    app.dependency_overrides[require_user] = lambda: User('owner', None, 'token')
    try:
        with TestClient(app) as client:
            for page in (1, 2):
                result = client.get('/api/discovery/jobs', params={
                    'q': 'Python', 'location': 'São Paulo', 'page': page,
                }).json()
                assert result['total'] == 1
                assert result['jobs'][0]['source'] == 'Jooble'
                assert result['jobs'][0]['description'] == 'Experiência em Python'
        assert len(calls) == 1
        assert calls[0].method == 'POST'
        assert calls[0].url.host == 'br.jooble.org'
        assert 'authorization' not in calls[0].headers
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_gupy_partner_feed_normalizes_company_jobs():
    jobs = list(discovery.gupy_jobs([{
        'name': 'Empresa', 'jobs': [{
            'title': 'Estágio', 'url': 'http://empresa.gupy.io/jobs/123',
            'address': {'city': 'São Paulo', 'country': 'BR'},
            'description': '<p>Desenvolvimento</p>', 'prerequisites': '<p>Python</p>',
            'remoteWorking': True,
        }],
    }]))
    assert len(jobs) == 1
    assert jobs[0]['url'] == 'https://empresa.gupy.io/jobs/123'
    assert jobs[0]['description'] == 'Desenvolvimento\nPython'
    assert jobs[0]['location'] == 'São Paulo, Brasil'
    assert jobs[0]['remote'] is True


def test_refresh_preserves_last_success_and_replaces_closed_jobs(monkeypatch, tmp_path):
    import asyncio

    monkeypatch.setenv('CAREEROS_DISCOVERY_CACHE_DIR', str(tmp_path))
    monkeypatch.setattr(discovery, '_cache', {})
    responses = iter([[{'title': 'Vaga', 'absolute_url': 'https://example.com/job/1'}],
                      ValueError('offline'), []])

    async def fetch(*args, **kwargs):
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(discovery, 'fetch_rows', fetch)

    async def scenario():
        jobs, ok = await discovery.get_feed('brex', force=True)
        assert ok and len(jobs) == 1
        first_update = discovery._cache['brex'].updated_at
        discovery._cache.clear()
        stale, ok = await discovery.get_feed('brex', force=True)
        assert not ok and stale == jobs
        assert discovery._cache['brex'].updated_at == first_update
        assert await discovery.get_feed('brex', force=True) == ([], True)

    asyncio.run(scenario())


def test_import_reads_jobposting_and_keeps_unsupported_urls_local(monkeypatch):
    calls = []

    async def fetch(method, url, **kwargs):
        calls.append(url)
        return b'''<script type="application/ld+json">{"@graph":[
            {"@type":"JobPosting","title":"Estagio Python","description":"<p>Aprenda</p>",
             "hiringOrganization":{"name":"Empresa"},"jobLocationType":"TELECOMMUTE"}]}</script>'''

    monkeypatch.setattr(discovery, 'fetch_content', fetch)
    monkeypatch.setattr(discovery, '_cache', {})
    app.dependency_overrides[require_user] = lambda: User('owner', None, 'token')
    try:
        with TestClient(app) as client:
            url = 'https://onjob.io/job/python-123'
            imported = client.get('/api/discovery/import', params={'url': url}).json()
            assert imported['company'] == 'Empresa'
            assert imported['description'] == 'Aprenda'
            assert imported['remote'] is True
            assert client.get('/api/discovery/import', params={'url': 'https://example.com/job/1'}).json() == {
                'url': 'https://example.com/job/1',
            }
            assert calls == [url]
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_career_url_only_accepts_configured_posting_paths():
    _, sitemap, prefix = discovery.ONJOB
    assert discovery.career_url('https://onjob.io/job/python-123', sitemap, prefix)
    for url in ('https://example.com/job/python', 'https://onjob.io/jobs/python',
                'https://onjob.io/job/../app', 'https://onjob.io/job/python?next=foo'):
        assert not discovery.career_url(url, sitemap, prefix)


def test_rss_and_atom_are_normalized_for_search():
    rss = b'''<rss version="2.0"><channel><item><title>Estagio Python</title>
        <link>https://example.com/jobs/1</link><description>&lt;p&gt;Remoto&lt;/p&gt;</description>
        </item></channel></rss>'''
    atom = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Analista</title>
        <link rel="self" href="https://example.com/feed/2"/>
        <link href="https://example.com/jobs/2"/><summary>Dados</summary></entry></feed>'''
    for content, url, description in ((rss, 'https://example.com/jobs/1', 'Remoto'),
                                      (atom, 'https://example.com/jobs/2', 'Dados')):
        job, = discovery.syndicated_jobs(content, 'Empresa')
        assert (job['url'], job['description'], job['source']) == (url, description, 'Empresa')


def test_sitemap_updates_good_postings_and_preserves_only_failed_pages(monkeypatch):
    import asyncio

    first = 'https://onjob.io/job/first'
    failed = 'https://onjob.io/job/failed'
    closed = 'https://onjob.io/job/closed'

    async def sitemap(*args, **kwargs):
        return f'<urlset><url><loc>{first}</loc></url><url><loc>{failed}</loc></url></urlset>'.encode()

    async def posting(url, *args):
        if url == failed:
            raise TimeoutError
        return {'url': url, 'title': 'Atualizada'}

    monkeypatch.setattr(discovery, 'fetch_content', sitemap)
    monkeypatch.setattr(discovery, 'fetch_career_job', posting)
    previous = [{'url': failed, 'title': 'Mantida'}, {'url': closed, 'title': 'Encerrada'}]
    jobs, partial = asyncio.run(discovery.career_jobs(*discovery.ONJOB, previous=previous))
    assert partial
    assert [job['title'] for job in jobs] == ['Atualizada', 'Mantida']


def test_search_reuses_snapshot_while_one_refresh_runs(monkeypatch):
    import asyncio

    calls = []
    jobs = [{'url': 'https://example.com/job/1'}]
    monkeypatch.setattr(discovery, '_cache', {'brex': discovery.Snapshot(0, jobs, True, '2026-11-04')})
    monkeypatch.setattr(discovery, '_refresh_tasks', {})

    async def slow_feed(key):
        calls.append(key)
        await asyncio.sleep(60)

    monkeypatch.setattr(discovery, 'get_feed', slow_feed)

    async def scenario():
        assert await discovery.search_feed('brex') == (jobs, True, True)
        assert await discovery.search_feed('brex') == (jobs, True, True)
        await asyncio.sleep(0)
        assert calls == ['brex']
        task = discovery._refresh_tasks['brex']
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())


def test_saved_searches_are_scoped_to_authenticated_account():
    calls = []
    owner = User('owner', None, 'token')
    search_id = 'af195512-52d8-4755-a8c6-f3e955c07d0a'

    class Store:
        user = owner

        async def rows(self, table, **filters):
            assert table == 'cloud_saved_searches'
            return [{'id': search_id, 'q': 'Python', 'location': '', 'remote': True}]

        async def request(self, method, path, **options):
            calls.append((method, path, options))

    app.dependency_overrides[require_user] = lambda: owner
    app.dependency_overrides[get_store] = Store
    try:
        with TestClient(app) as client:
            route = '/api/discovery/saved-searches'
            assert client.post(route, json={'q': ' Python ', 'remote': True}).status_code == 204
            assert client.get(route).json()[0]['q'] == 'Python'
            assert client.delete(route + '/' + search_id).status_code == 204
        assert calls[0][2]['json']['user_id'] == 'owner'
        assert calls[0][2]['json']['q'] == 'Python'
        assert calls[1][2]['params'] == {'id': 'eq.' + search_id, 'user_id': 'eq.owner'}
    finally:
        app.dependency_overrides.pop(require_user, None)
        app.dependency_overrides.pop(get_store, None)
