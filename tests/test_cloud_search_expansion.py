import asyncio
import json

import pytest

from app.cloud import discovery


@pytest.mark.parametrize('place', ['Presidente Prudente, SP', 'Santos, SP', 'Bauru - SP', 'Maceió, AL', 'Brasilândia, MS'])
def test_brazil_search_keeps_brazilian_cities_outside_the_old_shortlist(place):
    job = {'title':'Analista', 'location':place, 'remote':False}
    assert discovery.matches_location(job, 'brasil', 'onsite')


@pytest.mark.parametrize('place', ['Boston, MA, USA', 'Lisboa, Portugal', 'New York, NY', 'Remote, US only'])
def test_brazil_search_does_not_relax_foreign_location_restrictions(place):
    assert not discovery.matches_location({'title':'Engineer','location':place,'remote':False}, 'brasil', 'onsite')


@pytest.mark.parametrize('place,country', [('Boston, MA','US'), ('Santander, ES','ES'), ('Santa Maria','US'), ('Boston, MA','')])
def test_explicit_foreign_country_and_ambiguous_state_suffix_cannot_become_brazil(place, country):
    assert not discovery.matches_location({'title':'Engineer','location':place,'country_code':country,'remote':False}, 'brasil', 'onsite')


def test_ashby_keeps_foreign_country_attached_to_same_named_city():
    from app.cloud.public_catalogs import ashby_posting
    posting = ashby_posting({'title':'Engineer','location':'Santa Maria','address':{'postalAddress':{'addressCountry':'USA'}},
                            'jobUrl':'https://jobs.ashbyhq.com/demo/a','workplaceType':'OnSite'}, 'Demo')
    job = discovery.normalize(posting, 'Demo', '')
    assert not discovery.matches_location(job, 'brasil', 'onsite')


def test_malformed_workplace_metadata_does_not_abort_valid_source_records():
    from app.cloud.public_catalogs import ashby_posting, lever_posting
    assert ashby_posting({'workplaceType':[]}, 'Demo')['work_model'] == ''
    assert lever_posting({'workplaceType':{}}, 'Demo')['work_model'] == ''


@pytest.mark.parametrize('query,title', [
    ('desenvolvedor Python', 'Software Engineer Python'),
    ('desenvolvimento', 'Developer'), ('front-end', 'Frontend Developer'),
    ('backend', 'Back-end Engineer'), ('full stack', 'Fullstack Developer'),
    ('suporte tecnico', 'Technical Support Analyst'),
])
def test_role_variations_match_without_dropping_requested_terms(query, title):
    job = discovery.normalize({'title':title,'url':'https://jobs.example/1'}, 'Demo', '')
    assert discovery.best_match(job, [discovery.search_terms(query)], title_only=True, provider_matched=False)
    assert discovery.best_match(job, [discovery.search_terms(query + ' kotlin')], title_only=True, provider_matched=False) is None


def test_technical_support_keeps_separated_terms_matching():
    job = discovery.normalize({'title':'Suporte de TI','description':'Atendimento e suporte ao usuário. Curso técnico.',
                               'url':'https://jobs.example/support'}, 'Demo', '')
    assert discovery.best_match(job, [discovery.search_terms('suporte tecnico')], title_only=False, provider_matched=False)


def test_search_finds_explicit_internship_metadata_when_title_is_generic():
    job = discovery.normalize({'title':'Software Engineer','employment_type':'Intern',
                               'url':'https://jobs.example/intern'}, 'Demo', '')
    assert discovery.best_match(job, [discovery.search_terms('estagio')], title_only=False, provider_matched=False)


def test_ashby_preserves_remote_type_secondary_brazil_and_explicit_internship():
    from app.cloud.public_catalogs import collect_catalog
    async def fetch(*args, **kwargs):
        return json.dumps({'jobs':[
            {'id':'a','title':'Software Engineer','isListed':True,'workplaceType':'Hybrid','isRemote':True,
             'employmentType':'Intern','location':'San Francisco',
             'address':{'postalAddress':{'addressCountry':'USA'}},
             'secondaryLocations':[{'location':'Presidente Prudente','address':{'addressCountry':'BRA'}}],
             'descriptionPlain':'Python e SQL','jobUrl':'https://jobs.ashbyhq.com/demo/a',
             'applyUrl':'https://jobs.ashbyhq.com/demo/a/apply','publishedAt':'2026-11-01T12:00:00Z'},
            {'id':'hidden','title':'Unlisted','isListed':False,'jobUrl':'https://jobs.ashbyhq.com/demo/hidden'},
        ]}).encode()
    jobs, partial = asyncio.run(collect_catalog({'provider':'ashby','board':'demo','name':'Demo'}, fetch, discovery.normalize))
    assert not partial
    assert len(jobs) == 1
    assert jobs[0]['work_model'] == 'hybrid'
    assert jobs[0]['employment_type'] == 'Intern'
    assert jobs[0]['published_at'] == '2026-11-01T12:00:00Z'
    assert discovery.matches_location(jobs[0], 'brasil', 'hybrid')
    assert discovery.matches_level(jobs[0], 'intern')


def test_lever_collects_more_than_one_page_and_keeps_application_url():
    from app.cloud.public_catalogs import collect_catalog, PAGE_SIZE
    calls = []
    async def fetch(method, url, **options):
        skip = options['params']['skip']
        calls.append(skip)
        rows = [{'id':str(skip+i),'text':'Developer','country':'BR','categories':{'location':'Brasil'},
                 'descriptionPlain':'Python','workplaceType':'remote',
                 'hostedUrl':f'https://jobs.lever.co/demo/{skip+i}',
                 'applyUrl':f'https://jobs.lever.co/demo/{skip+i}/apply'} for i in range(PAGE_SIZE if skip == 0 else 1)]
        return json.dumps(rows).encode()
    jobs, partial = asyncio.run(collect_catalog({'provider':'lever','board':'demo','name':'Demo'}, fetch, discovery.normalize))
    assert len(jobs) == PAGE_SIZE + 1
    assert calls == [0, PAGE_SIZE]
    assert not partial
    assert jobs[-1]['apply_url'].endswith('/apply')
    assert jobs[-1]['work_model'] == 'remote'


def test_lever_repeated_page_stops_without_duplicate_results():
    from app.cloud.public_catalogs import collect_catalog, PAGE_SIZE
    calls = []
    async def fetch(*args, **kwargs):
        calls.append(1)
        return json.dumps([{'id':str(i),'text':'Analista','hostedUrl':f'https://jobs.lever.co/demo/{i}'} for i in range(PAGE_SIZE)]).encode()
    jobs, partial = asyncio.run(collect_catalog({'provider':'lever','board':'demo','name':'Demo'}, fetch, discovery.normalize))
    assert len(jobs) == PAGE_SIZE
    assert len(calls) == 2
    assert partial


def test_catalog_validation_rejects_arbitrary_urls_and_invalid_board_paths():
    from app.cloud.public_catalogs import validate_sources
    for row in [{'provider':'other','board':'demo','name':'Demo'},
                {'provider':'ashby','board':'../../private','name':'Demo'},
                {'provider':'lever','board':'demo','name':'Demo','url':'http://127.0.0.1'}]:
        with pytest.raises(ValueError):
            validate_sources([row])


def test_partial_public_refresh_preserves_unseen_cached_jobs(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    key = 'lever_ciandt'
    old = discovery.normalize({'title':'Old','url':'https://jobs.example/old'}, 'Demo', '')
    fresh = discovery.normalize({'title':'Fresh','url':'https://jobs.example/fresh'}, 'Demo', '')
    monkeypatch.setenv('CAREEROS_DISCOVERY_CACHE_DIR', str(tmp_path))
    monkeypatch.setattr(discovery, '_cache', {key:discovery.Snapshot(0,[old],True,datetime.now(timezone.utc).isoformat())})
    async def collect(*args): return [fresh], True
    monkeypatch.setattr(discovery, 'collect_catalog', collect)
    jobs, available = asyncio.run(discovery.get_feed(key, force=True))
    assert [job['title'] for job in jobs] == ['Fresh','Old']
    assert not available
    assert discovery._cache[key].partial


def test_fresh_publication_breaks_relevance_ties_but_not_title_priority():
    from app.cloud.discovery import publication_timestamp
    assert publication_timestamp('2026-11-02T10:00:00Z') > publication_timestamp('2026-10-01T10:00:00Z')
    assert publication_timestamp('unknown') == 0


def test_search_orders_real_results_by_relevance_then_publication(monkeypatch):
    from fastapi.testclient import TestClient
    from app.cloud.main import app
    from app.cloud.auth import require_user, User
    def job(suffix, title, text, published):
        return discovery.normalize({'title':title,'url':'https://jobs.example/' + suffix,
                                    'description':text,'published_at':published}, 'Demo', '')
    rows = [job('older', 'Python Developer', 'Python ' * 100, '2026-01-01T00:00:00Z'),
            job('newer', 'Python Developer', 'Python', '2026-11-01T00:00:00Z'),
            job('details', 'Analista', 'Python', '2026-11-05T00:00:00Z')]
    async def feed(key): return (rows if key == 'brex' else []), True
    monkeypatch.setattr(discovery, 'get_feed', feed)
    monkeypatch.setattr(discovery, '_cache', {})
    app.dependency_overrides[require_user] = lambda: User('owner', None, 'token')
    try:
        with TestClient(app) as client:
            response = client.get('/api/discovery/jobs', params={'q':'Python'})
        assert response.status_code == 200
        assert [row['url'].rsplit('/', 1)[1] for row in response.json()['jobs']] == ['newer','older','details']
        assert response.json()['search_summary']['catalog_listings'] == 3
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_registered_ashby_catalog_reaches_authenticated_search(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from app.cloud.main import app
    from app.cloud.auth import require_user, User
    key = 'ashby_demo'
    original = discovery.get_feed
    async def get_feed(source, *args):
        return await original(source, *args) if source == key else ([], True)
    async def fetch(*args, **kwargs):
        return json.dumps({'jobs':[{'title':'Software Engineer','employmentType':'Intern',
            'isListed':True,'workplaceType':'Remote','location':'Presidente Prudente',
            'address':{'postalAddress':{'addressCountry':'BRA'}},'descriptionPlain':'Python',
            'jobUrl':'https://jobs.ashbyhq.com/demo/intern'}]}).encode()
    async def region(*args):
        return SimpleNamespace(jobs=[],available=False,reason='provider_not_configured',sources=[]),False
    monkeypatch.setattr(discovery, 'PUBLIC_SOURCES', {key:{'provider':'ashby','board':'demo','name':'Demo'}})
    monkeypatch.setattr(discovery, '_locks', {key:asyncio.Lock()})
    monkeypatch.setattr(discovery, '_cache', {})
    monkeypatch.setattr(discovery, '_refresh_tasks', {})
    monkeypatch.setattr(discovery, 'get_feed', get_feed)
    monkeypatch.setattr(discovery, 'fetch_content', fetch)
    monkeypatch.setattr(discovery, 'enabled_aggregators', lambda: [])
    monkeypatch.setattr(discovery.source_discovery, 'regional_feed', region)
    monkeypatch.setenv('CAREEROS_DISCOVERY_CACHE_DIR', str(tmp_path))
    app.dependency_overrides[require_user] = lambda: User('owner', None, 'token')
    try:
        with TestClient(app) as client:
            response = client.get('/api/discovery/jobs', params={'q':'estagio python','level':'intern','location':'Brasil','work_model':'remote'})
        assert response.status_code == 200
        assert response.json()['total'] == 1
        assert response.json()['jobs'][0]['source'] == 'Demo · Ashby'
    finally:
        app.dependency_overrides.pop(require_user, None)
