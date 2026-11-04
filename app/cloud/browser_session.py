import os
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .config import settings

SESSION = '__Secure-careeros-session'
REMEMBERED = '__Secure-careeros-remembered'
PATH = '/api/auth/session'
REMEMBER_SECONDS = 30 * 24 * 3600


def same_origin(request: Request):
    origin = request.headers.get('origin')
    app_url = os.getenv('APP_URL', '').rstrip('/')
    local_origin = str(request.base_url).rstrip('/')
    try:
        parsed = urlsplit(origin or '')
    except ValueError:
        raise HTTPException(403, 'Origem inválida para esta operação.') from None
    local = parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if not origin or origin not in (app_url, local_origin) or (parsed.scheme != 'https' and not local):
        raise HTTPException(403, 'Origem inválida para esta operação.')


router = APIRouter(prefix=PATH, dependencies=[Depends(same_origin)])


class SessionInput(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1, max_length=1024)
    remember: bool = False


def clear_cookies(response):
    for name in (SESSION, REMEMBERED):
        response.delete_cookie(name, path=PATH, secure=True, httponly=True, samesite='lax')


async def auth_request(path, *, token=None, payload=None):
    config = settings()
    if not config.configured:
        raise HTTPException(503, 'Login indisponível neste ambiente.')
    headers = {'apikey': config.supabase_anon_key}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(config.supabase_url + path, headers=headers, json=payload)
    except httpx.HTTPError:
        raise HTTPException(503, 'Não foi possível acessar o serviço de login.') from None
    if response.status_code >= 500 or response.status_code == 429:
        raise HTTPException(503, 'O serviço de login está temporariamente indisponível.')
    return response


@router.post('')
async def browser_session(data: SessionInput, request: Request, response: Response):
    remembered = request.cookies.get(REMEMBERED)
    refresh = data.refresh_token or request.cookies.get(SESSION) or remembered
    if not refresh:
        return {'session': None}
    persist = data.remember if data.refresh_token else bool(remembered and refresh == remembered)
    upstream = await auth_request('/auth/v1/token?grant_type=refresh_token', payload={'refresh_token': refresh})
    if upstream.status_code in (400, 401, 403):
        clear_cookies(response)
        if data.refresh_token:
            response.status_code = 401
        return {'session': None}
    try:
        result = upstream.json()
        access, rotated, lifetime, user = (result[key] for key in ('access_token', 'refresh_token', 'expires_in', 'user'))
        if (upstream.status_code != 200 or not isinstance(access, str) or not isinstance(rotated, str)
                or not isinstance(lifetime, int) or not isinstance(user, dict) or not isinstance(user.get('id'), str)):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise HTTPException(503, 'Resposta inválida do serviço de login.') from None
    clear_cookies(response)
    response.set_cookie(REMEMBERED if persist else SESSION, rotated, path=PATH,
                        max_age=REMEMBER_SECONDS if persist else None,
                        secure=True, httponly=True, samesite='lax')
    return {'session': {'access_token': access, 'expires_in': lifetime, 'user': user}}


@router.delete('', status_code=204)
async def end_browser_session(request: Request, response: Response):
    scheme, _, token = request.headers.get('authorization', '').partition(' ')
    if scheme.lower() == 'bearer' and token:
        upstream = await auth_request('/auth/v1/logout?scope=local', token=token)
        if upstream.status_code not in (200, 204, 401, 403, 404):
            raise HTTPException(503, 'Não foi possível encerrar a sessão.')
    clear_cookies(response)
