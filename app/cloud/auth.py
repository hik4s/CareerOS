from dataclasses import dataclass
from uuid import UUID
import httpx
from fastapi import HTTPException, Request
from .config import settings

@dataclass(frozen=True)
class User:
    id: str
    email: str | None
    token: str

async def require_user(request: Request) -> User:
    config = settings()
    if not config.configured:
        raise HTTPException(503, 'Cloud authentication is not configured')
    authorization = request.headers.get('authorization', '')
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(config.supabase_url + '/auth/v1/user', headers={'apikey': config.supabase_anon_key, 'Authorization': 'Bearer ' + token})
        if response.status_code != 200:
            raise HTTPException(401, 'Invalid or expired session')
        payload = response.json()
        uid = str(UUID(payload['id']))
        return User(uid, payload.get('email'), token)
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Unable to validate session') from None
