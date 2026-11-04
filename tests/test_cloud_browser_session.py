import httpx
from fastapi.testclient import TestClient

from app.cloud import browser_session
from app.cloud.main import app


ORIGIN = 'https://careeros.example'


def test_browser_session_rotates_refresh_cookie_and_only_persists_on_request(monkeypatch):
    calls = []

    async def upstream(path, *, token=None, payload=None):
        calls.append((path, token, payload))
        if 'logout' in path:
            return httpx.Response(204)
        return httpx.Response(200, json={
            'access_token': 'access', 'refresh_token': 'rotated',
            'expires_in': 3600, 'user': {'id': 'owner'},
        })

    monkeypatch.setattr(browser_session, 'auth_request', upstream)
    with TestClient(app, base_url=ORIGIN) as client:
        rejected = client.post(browser_session.PATH, json={}, headers={'Origin': 'https://other.example'})
        assert rejected.status_code == 403
        assert not calls

        for remember in (False, True):
            logged_in = client.post(browser_session.PATH, json={
                'refresh_token': 'original', 'remember': remember,
            }, headers={'Origin': ORIGIN})
            assert logged_in.status_code == 200
            assert logged_in.json()['session']['access_token'] == 'access'
            assert 'refresh_token' not in logged_in.json()['session']
            cookie_name = browser_session.REMEMBERED if remember else browser_session.SESSION
            cookie = next(value for value in logged_in.headers.get_list('set-cookie')
                          if value.startswith(f'{cookie_name}=rotated;'))
            assert all(flag in cookie for flag in ('HttpOnly', 'Secure', 'SameSite=lax'))
            assert ('Max-Age=' in cookie) is remember
            assert logged_in.headers['cache-control'] == 'no-store'

        restored = client.post(browser_session.PATH, json={}, headers={'Origin': ORIGIN})
        assert restored.status_code == 200
        assert calls[-1][2] == {'refresh_token': 'rotated'}
        signed_out = client.delete(browser_session.PATH, headers={
            'Origin': ORIGIN, 'Authorization': 'Bearer access',
        })
        assert signed_out.status_code == 204
        assert calls[-1][1] == 'access'
        assert client.post(browser_session.PATH, json={}, headers={'Origin': ORIGIN}).json() == {'session': None}
