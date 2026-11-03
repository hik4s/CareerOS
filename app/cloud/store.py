from uuid import uuid4
import httpx
from fastapi import Depends, HTTPException
from .auth import User, require_user
from .config import settings

class SupabaseStore:
    def __init__(self, user: User):
        self.user = user
        self.config = settings()

    async def request(self, method, path, *, params=None, json=None, content=None, headers=None):
        if not self.config.configured:
            raise HTTPException(503, 'Cloud storage is not configured')
        auth = {'apikey': self.config.supabase_anon_key, 'Authorization': f'Bearer {self.user.token}', **(headers or {})}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                result = await client.request(method, self.config.supabase_url + path, params=params, json=json, content=content, headers=auth)
            if result.status_code >= 400:
                raise HTTPException(502, 'Cloud storage request failed')
            return result.json() if result.content else None
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, 'Cloud storage is unavailable') from None

    async def rows(self, table, **filters):
        return await self.request('GET', '/rest/v1/' + table, params={'user_id': 'eq.' + self.user.id, **filters})

    async def insert(self, table, data):
        payload = {**data, 'user_id': self.user.id}
        result = await self.request('POST', '/rest/v1/' + table, json=payload, headers={'Prefer': 'return=representation'})
        return result[0]

    async def profile(self):
        rows = await self.rows('cloud_profiles', limit='1')
        return rows[0]['data'] if rows else {}

    async def save_profile(self, data):
        await self.request('POST', '/rest/v1/cloud_profiles', params={'on_conflict': 'user_id'}, json={'user_id': self.user.id, 'data': data}, headers={'Prefer': 'resolution=merge-duplicates'})
        return data

    async def jobs(self):
        return await self.rows('cloud_jobs', order='created_at.desc')

    async def job(self, id):
        rows = await self.rows('cloud_jobs', id='eq.' + str(id), limit='1')
        if not rows:
            raise HTTPException(404, 'Job not found')
        return rows[0]

    async def create_job(self, data):
        return await self.insert('cloud_jobs', {**data, 'id': str(uuid4())})

    async def update_job(self, id, data):
        result = await self.request('PATCH', '/rest/v1/cloud_jobs', params={'id': 'eq.' + str(id), 'user_id': 'eq.' + self.user.id}, json=data, headers={'Prefer': 'return=representation'})
        if not result:
            raise HTTPException(404, 'Job not found')
        return result[0]

    async def delete_job(self, id):
        await self.job(id)
        await self.request('DELETE', '/rest/v1/cloud_jobs', params={'id': 'eq.' + str(id), 'user_id': 'eq.' + self.user.id})

    async def ai_history(self, limit=20):
        return await self.rows('cloud_ai_runs', order='created_at.desc', limit=str(min(max(limit, 1), 100)))

    async def ai_cached(self, fingerprint):
        rows = await self.rows('cloud_ai_runs', request_hash='eq.' + fingerprint, order='created_at.desc', limit='1')
        return rows[0] if rows else None

    async def save_ai_run(self, data):
        return await self.insert('cloud_ai_runs', {**data, 'id': str(uuid4())})

def get_store(user: User = Depends(require_user)) -> SupabaseStore:
    return SupabaseStore(user)
