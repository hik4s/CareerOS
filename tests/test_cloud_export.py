import asyncio
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from uuid import uuid4
from zipfile import ZipFile

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.cloud.auth import User
from app.cloud.main import app
from app.cloud.store import SupabaseStore, get_store
from app.cloud.export import build_export, all_rows

OWNER = '11111111-1111-4111-8111-111111111111'
RID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'


class Store:
    user = SimpleNamespace(id=OWNER, token='never-export-this-token')
    def __init__(self):
        self.downloads = []
    async def profile(self):
        return {'full_name': 'Exemplo', 'skills': ['python']}
    async def rows(self, table, **filters):
        assert filters['order'] == 'id.asc'
        assert 'created_at' in filters
        if int(filters['offset']):
            return []
        return {'cloud_jobs': [{'id': str(uuid4()), 'user_id': OWNER, 'title': 'Estágio'}],
                'cloud_ai_runs': [{'id': str(uuid4()), 'user_id': OWNER, 'result': 'Texto factual', 'input_tokens': 20}],
                'cloud_resumes': [{'id': RID, 'user_id': OWNER, 'filename': '../../original.pdf', 'storage_path': OWNER + '/' + RID + '.pdf'}]}[table]
    async def resume_bytes(self, path, max_bytes):
        self.downloads.append(path)
        return b'%PDF-synthetic'


def test_export_contains_records_files_and_integrity_manifest(tmp_path):
    store = Store()
    path = asyncio.run(build_export(store, tmp_path))
    with ZipFile(path) as archive:
        assert set(archive.namelist()) == {'workspace.json', 'manifest.json', f'resumes/{RID}.pdf'}
        data = json.loads(archive.read('workspace.json'))
        assert data['profile']['full_name'] == 'Exemplo'
        assert data['jobs'][0]['title'] == 'Estágio'
        assert data['ai_history'][0]['input_tokens'] == 20
        assert data['resumes'][0]['archive_path'] == f'resumes/{RID}.pdf'
        assert 'never-export-this-token' not in archive.read('workspace.json').decode()
        manifest = json.loads(archive.read('manifest.json'))
        for name, expected in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected


def test_export_rejects_foreign_metadata_even_if_backend_misconfigured(tmp_path):
    class Foreign(Store):
        async def rows(self, table, **filters):
            return [{'id': RID, 'user_id': '22222222-2222-4222-8222-222222222222'}]
    with pytest.raises(HTTPException) as error:
        asyncio.run(build_export(Foreign(), tmp_path))
    assert error.value.status_code == 502
    assert not (tmp_path / 'CareerOS-workspace.zip').exists()


def test_pagination_exports_more_than_first_page():
    class Pages:
        async def rows(self, table, **filters):
            offset = int(filters['offset'])
            return [{'id': str(i), 'user_id': OWNER} for i in range(offset, min(offset + 250, 510))]
    rows = asyncio.run(all_rows(Pages(), 'cloud_jobs', '2026-11-03T00:00:00+00:00'))
    assert len(rows) == 510


def test_server_page_cap_does_not_silently_truncate():
    class Pages:
        async def rows(self, table, **filters):
            offset = int(filters['offset'])
            return [{'id': str(i), 'user_id': OWNER} for i in range(offset, min(offset + 30, 95))]
    assert len(asyncio.run(all_rows(Pages(), 'cloud_jobs', '2026-11-03T00:00:00+00:00'))) == 95


def test_oversized_export_is_cleaned_up(monkeypatch, tmp_path):
    import app.cloud.export as module
    monkeypatch.setattr(module, 'MAX_BYTES', 100)
    with pytest.raises(HTTPException) as error:
        asyncio.run(build_export(Store(), tmp_path))
    assert error.value.status_code == 413
    assert not (tmp_path / 'CareerOS-workspace.zip').exists()


def test_file_failure_does_not_return_incomplete_zip(tmp_path):
    class Failing(Store):
        async def resume_bytes(self, path, max_bytes):
            raise HTTPException(502, 'Storage indisponível')
    with pytest.raises(HTTPException):
        asyncio.run(build_export(Failing(), tmp_path))
    assert not (tmp_path / 'CareerOS-workspace.zip').exists()


def test_export_route_requires_authentication(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    with TestClient(app) as client:
        assert client.get('/api/workspace/export.zip').status_code == 401


def test_route_streams_valid_zip_and_cleans_temporary_directory(monkeypatch, tmp_path):
    import app.cloud.export as module
    original = tempfile.mkdtemp
    created = []
    def temporary(**kwargs):
        folder = original(dir=tmp_path, **kwargs)
        created.append(Path(folder))
        return folder
    monkeypatch.setattr(module.tempfile, 'mkdtemp', temporary)
    app.dependency_overrides[get_store] = lambda: Store()
    try:
        with TestClient(app) as client:
            response = client.get('/api/workspace/export.zip')
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'no-store'
            with ZipFile(BytesIO(response.content)) as archive:
                assert 'workspace.json' in archive.namelist()
        assert created and all(not folder.exists() for folder in created)
    finally:
        app.dependency_overrides.clear()


def test_download_is_owner_bound_and_does_not_follow_redirects(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'public-anon')
    original = httpx.AsyncClient
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers['authorization'] == 'Bearer session'
        assert request.url.path == f'/storage/v1/object/authenticated/career-resumes/{OWNER}/{RID}.pdf'
        return httpx.Response(200, content=b'%PDF-file')
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    store = SupabaseStore(User(OWNER, None, 'session'))
    assert asyncio.run(store.resume_bytes(OWNER + '/' + RID + '.pdf', 1024)) == b'%PDF-file'
    with pytest.raises(HTTPException):
        asyncio.run(store.resume_bytes('22222222-2222-4222-8222-222222222222/' + RID + '.pdf', 1024))
    assert len(calls) == 1
