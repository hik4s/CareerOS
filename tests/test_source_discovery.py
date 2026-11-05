import asyncio
import socket
from unittest.mock import patch

import pytest

from app.cloud import source_discovery as regional


@pytest.mark.parametrize('url', [
    'http://example.com/jobs', 'https://user:password@example.com/jobs',
    'https://example.com:8443/jobs', 'https://localhost/jobs',
    'https://example.com\\@127.0.0.1/jobs', 'https://[::1]/jobs',
])
def test_source_url_rejects_unsafe_destinations(url):
    with pytest.raises(ValueError):
        regional.public_url(url)


def test_dns_rebinding_cannot_connect_to_a_private_address():
    connection = regional.PublicHTTPS('example.com')
    records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]
    with patch.object(socket, 'getaddrinfo', return_value=records), patch.object(socket, 'create_connection') as connect:
        with pytest.raises(ValueError):
            connection.connect()
        connect.assert_not_called()


def test_source_links_stay_on_same_host_and_are_bounded():
    parser = regional.PostingLinks('https://example.com/vagas')
    parser.feed('''<a href="/vagas/1">One</a><a href="https://evil.example/vagas/2">Two</a>
      <a href="/jobs/3">Three</a><a href="/vagas/4">Four</a>''')
    assert parser.links == ['https://example.com/vagas/1', 'https://example.com/jobs/3']


def test_discovery_keeps_links_distinct_from_verified_jobs(monkeypatch):
    async def scenario():
        async def search(*args):
            return [
                {'link': 'https://local.example/vagas'},
                {'link': 'https://company.example/jobs/1'},
            ]
        def page(url):
            return '<html>listing</html>' if 'local.example' in url else '<html>job</html>'
        def parse(markup, url, host):
            if markup == '<html>listing</html>':
                raise ValueError('No JobPosting')
            return {'title': 'Python', 'url': url, 'source': host}
        monkeypatch.setattr(regional, 'search_sources', search)
        monkeypatch.setattr(regional, 'permitted_page', page)
        monkeypatch.setattr(regional, '_budget_count', 0)
        result = await regional.collect_region('Curitiba', None, parse)
        assert len(result.jobs) == 1
        assert result.sources[0]['status'] == 'needs_adapter'
        assert result.sources[1]['status'] == 'integrated'
    asyncio.run(scenario())


def test_city_cache_is_shared_and_does_not_wait_for_collection(monkeypatch):
    async def scenario():
        gate = asyncio.Event()
        calls = []
        async def collect(*args):
            calls.append(args[0])
            await gate.wait()
            return regional.RegionSnapshot(9999999999, [], [], True)
        monkeypatch.setattr(regional, 'provider', lambda: 'searchapi')
        monkeypatch.setattr(regional, 'read_region', lambda key: None)
        monkeypatch.setattr(regional, 'save_region', lambda *args: None)
        monkeypatch.setattr(regional, 'collect_region', collect)
        monkeypatch.setattr(regional, '_cache', {})
        monkeypatch.setattr(regional, '_tasks', {})
        results = await asyncio.gather(
            regional.regional_feed('Presidente Prudente', None, None),
            regional.regional_feed('Presidente Prudente, SP', None, None),
        )
        assert [pending for _, pending in results] == [True, True]
        assert len(calls) == 1
        gate.set()
        await asyncio.gather(*regional._tasks.values())
        _, pending = await regional.regional_feed('Presidente Prudente', None, None)
        assert not pending
    asyncio.run(scenario())


def test_unconfigured_provider_is_reported_without_network(monkeypatch):
    monkeypatch.delenv('CAREEROS_SEARCHAPI_API_KEY', raising=False)
    monkeypatch.delenv('CAREEROS_SERPAPI_API_KEY', raising=False)
    result, pending = asyncio.run(regional.regional_feed('Recife', None, None))
    assert result.reason == 'provider_not_configured'
    assert not pending


def test_public_connection_pins_ip_and_keeps_certificate_hostname():
    from unittest.mock import Mock
    context = Mock()
    connection = regional.PublicHTTPS('jobs.example.com', context=context)
    records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]
    with patch.object(socket, 'getaddrinfo', return_value=records), patch.object(socket, 'create_connection') as connect:
        connection.connect()
        connect.assert_called_once_with(('8.8.8.8', 443), timeout=connection.timeout)
        context.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='jobs.example.com', do_handshake_on_connect=False)
        context.wrap_socket.return_value.do_handshake.assert_called_once()


def test_robots_disallow_prevents_page_collection(monkeypatch):
    calls = []
    def page(url):
        calls.append(url)
        return 200, b'User-agent: *\nDisallow: /vagas'
    monkeypatch.setattr(regional, 'public_page', page)
    with pytest.raises(ValueError, match='disallows'):
        regional.permitted_page('https://jobs.example.com/vagas')
    assert calls == ['https://jobs.example.com/robots.txt']


@pytest.mark.parametrize('city', ['Curitiba', 'Recife'])
def test_discovery_imports_real_structured_format_for_different_regions(monkeypatch, city):
    import json
    from app.cloud.discovery import structured_job
    async def scenario():
        async def search(*args):
            return [{'link': 'https://jobs.example.com/vagas/python'}]
        posting = {'@context': 'https://schema.org', '@type': 'JobPosting',
                   'title': 'Estágio Python', 'description': 'Desenvolvimento de software Python',
                   'hiringOrganization': {'name': 'Empresa Exemplo'},
                   'jobLocation': {'address': {'addressLocality': city, 'addressCountry': 'BR'}}}
        monkeypatch.setattr(regional, 'search_sources', search)
        monkeypatch.setattr(regional, 'permitted_page', lambda url: '<script type="application/ld+json">'+json.dumps(posting)+'</script>')
        monkeypatch.setattr(regional, '_cache', {})
        monkeypatch.setattr(regional, '_budget_count', 0)
        result = await regional.collect_region(city, None, structured_job)
        assert len(result.jobs) == 1
        assert city in result.jobs[0]['location']
        assert result.sources[0]['status'] == 'integrated'
    asyncio.run(scenario())


def test_stalled_dns_releases_caller_and_bounds_lookup_threads(monkeypatch):
    import threading
    from unittest.mock import Mock
    gate = threading.Event()
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(regional, '_resolver_slots', slots)
    def stalled(*args, **kwargs):
        gate.wait(5)
        return []
    monkeypatch.setattr(socket, 'getaddrinfo', stalled)
    fake_queue = Mock()
    fake_queue.get.side_effect = regional.queue.Empty
    monkeypatch.setattr(regional.queue, 'Queue', lambda **kwargs: fake_queue)
    try:
        with pytest.raises(TimeoutError, match='DNS timeout'):
            regional.resolve_public_host('example.com')
        fake_queue.get.assert_called_once_with(timeout=2)
        with pytest.raises(TimeoutError, match='resolver busy'):
            regional.resolve_public_host('example.com')
    finally:
        gate.set()
