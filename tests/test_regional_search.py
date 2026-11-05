import asyncio
import time

from app.cloud import discovery
from app.cloud.job_fit import career_fit
from app.cloud.regional_jobs import InovaCards


def test_inova_only_reads_current_job_cards_and_city():
    parser = InovaCards()
    parser.feed('''<a href="https://inovaprudente.com.br/vagas/1124/estagio-em-ti" title="Estágio em T.I.">
        <h2>Estágio em T.I.</h2><span>Estágio</span><span>Presencial</span>
        <p><strong>Cidade:</strong> <i>Presidente Prudente</i></p><p>Redes, Windows e Linux</p>
        <!-- <a href=""> commented markup is not a new posting --></a>
        <a href="https://evil.example/vagas/1/falsa" title="Falsa">Cidade: Presidente Prudente</a>''')
    row, = parser.cards
    job = discovery.normalize(row, 'Inova Prudente', '')
    assert job['location'] == 'Presidente Prudente'
    assert job['work_model'] == 'onsite'
    assert discovery.best_match(job, [discovery.search_terms('estágio ti')], title_only=True, provider_matched=False)


def test_profile_removes_unrelated_internships_and_senior_positions():
    profile = {'skills': ['Python', 'SQL'], 'target_roles': ['Estágio desenvolvimento']}
    for title, description in [
        ('Estágio contábil', 'Emissão de notas fiscais'),
        ('Engenheiro civil sênior', 'Gestão de obras'),
        ('Desenvolvedor Python Sênior', 'Python e APIs'),
    ]:
        assert not career_fit({'title': title, 'description': description}, profile, '')[0]
    fits, reasons = career_fit({'title': 'Estágio em T.I.', 'description': 'Suporte, redes e Linux'}, profile, '')
    assert fits
    assert 'Área de tecnologia identificada' in reasons


def test_jooble_separates_alternatives_and_keeps_location(monkeypatch):
    calls = []
    async def feed(key, query, location, remote):
        calls.append((query, location))
        return [], True, False
    monkeypatch.setattr(discovery, 'jooble_feed', feed)
    result = asyncio.run(discovery.jooble_alternatives('secret', 'estágio, python, ai builder, estágio', 'Presidente Prudente', False))
    assert calls == [('estágio', 'Presidente Prudente'), ('python', 'Presidente Prudente'), ('ai builder', 'Presidente Prudente')]
    assert result == ([], True, False)


def test_aggregator_uses_requested_query_and_city_and_reuses_cache(monkeypatch):
    async def scenario():
        calls = []
        async def adapter(key, token, query, location):
            calls.append((key, query, location))
            return []
        monkeypatch.setattr(discovery, 'aggregator_jobs', adapter)
        monkeypatch.setattr(discovery, '_query_cache', {})
        monkeypatch.setattr(discovery, '_query_tasks', {})
        for _ in range(2):
            assert await discovery.query_aggregator('serpapi_google', 'python, software', 'Presidente Prudente', False) == ([], True, False)
        assert calls == [('serpapi_google', '((python) OR (software))', 'Presidente Prudente')]
    asyncio.run(scenario())


def test_cold_sources_do_not_delay_fast_local_feed(monkeypatch):
    async def scenario():
        tasks = {}
        async def slow(key, *args):
            await asyncio.sleep(.1)
            return [], True
        monkeypatch.setattr(discovery, 'get_feed', slow)
        monkeypatch.setattr(discovery, '_refresh_tasks', tasks)
        monkeypatch.setattr(discovery, '_cache', {})
        # Shared wait is concurrent, not one timeout per source in series.
        started = time.monotonic()
        await asyncio.gather(*(discovery.search_feed(key) for key in ('brex', 'inova', 'careers')))
        assert time.monotonic() - started < .25
    asyncio.run(scenario())


def test_unrelated_internship_is_not_allowed_by_employer_boilerplate():
    job = {'title': 'Estágio administrativo', 'description': 'Somos uma empresa de software que usa Python.'}
    assert not career_fit(job, {'skills': ['Python']}, 'estágio')[0]


def test_requested_city_reaches_external_search(monkeypatch):
    async def scenario():
        calls = []
        async def rows(method, url, field, **options):
            calls.append(options['params'])
            return []
        monkeypatch.setattr(discovery, 'fetch_rows', rows)
        await discovery.aggregator_jobs('serpapi_google', 'test', '(python)', 'Presidente Prudente')
        assert calls[0]['q'] == '(python) Presidente Prudente'
        assert calls[0]['gl'] == 'br'
    asyncio.run(scenario())


def test_city_with_state_matches_local_source_without_state_suffix():
    job = {'title': 'Estágio em TI', 'location': 'Presidente Prudente', 'remote': False}
    assert discovery.matches_location(job, 'presidente prudente, sp', 'onsite')
    assert not discovery.matches_location(job, 'sao paulo, sp', 'onsite')
