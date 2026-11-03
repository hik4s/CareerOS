import hashlib
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.updates import UpdateService, parse_release


def release(version='0.8.0', content=b'MZinstaller'):
    name = f'CareerOS-Setup-{version}.exe'
    url = f'https://github.com/hik4s/CareerOS/releases/download/v{version}/'
    return {'tag_name': f'v{version}', 'draft': False, 'prerelease': False,
            'body': 'Novidades', 'html_url': f'https://github.com/hik4s/CareerOS/releases/tag/v{version}',
            'assets': [{'name': name, 'browser_download_url': url + name, 'size': len(content)},
                       {'name': name + '.sha256', 'browser_download_url': url + name + '.sha256', 'size': 100}]}


def client_for(data, content=b'MZinstaller', checksum=None):
    def handle(request):
        if request.url.host == 'api.github.com':
            return httpx.Response(200, json=data)
        if request.url.path.endswith('.sha256'):
            return httpx.Response(200, text=checksum or hashlib.sha256(content).hexdigest())
        return httpx.Response(200, content=content)
    return httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True)


def test_available_update_and_verified_download(tmp_path):
    service = UpdateService(tmp_path, client=client_for(release()), current='0.7.0')
    assert service.check()['state'] == 'available'
    path = service.download()
    assert path.read_bytes() == b'MZinstaller'
    assert service.status()['state'] == 'ready'


def test_corruption_blocks_execution(tmp_path):
    service = UpdateService(tmp_path, client=client_for(release(), checksum='0' * 64), current='0.7.0')
    service.check()
    with pytest.raises(ValueError, match='integridade'):
        service.download()
    assert not list(tmp_path.glob('*.exe'))
    assert service.status()['state'] == 'error'


@pytest.mark.parametrize('version', ['0.7.0', '0.6.0'])
def test_no_downgrade(version, tmp_path):
    service = UpdateService(tmp_path, client=client_for(release(version)), current='0.7.0')
    assert service.check()['state'] == 'current'


def test_no_release_is_not_an_error(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(404)))
    assert UpdateService(tmp_path, client=client).check()['state'] == 'no_release'


@pytest.mark.parametrize('mutation', ['draft', 'prerelease', 'wrong_url', 'missing_hash'])
def test_incomplete_or_untrusted_release_rejected(mutation):
    data = release()
    if mutation in {'draft', 'prerelease'}:
        data[mutation] = True
    elif mutation == 'wrong_url':
        data['assets'][0]['browser_download_url'] = 'https://evil.example/installer.exe'
    else:
        data['assets'].pop()
    with pytest.raises(ValueError):
        parse_release(data)


def test_offline_does_not_break_startup(tmp_path):
    def offline(request):
        raise httpx.ConnectError('offline', request=request)
    client = httpx.Client(transport=httpx.MockTransport(offline))
    assert UpdateService(tmp_path, client=client).check()['state'] == 'offline'
