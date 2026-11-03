"""Explicit per-account export; no credentials, public links or database dumps."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from .store import SupabaseStore, get_store
from .version import VERSION

router = APIRouter(prefix='/api/workspace', tags=['Workspace'])
MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 10000
_export_gate = asyncio.Lock()


async def all_rows(store, table, started, budget=None, owner_id=None):
    result = []
    offset = 0
    page_size = 100
    while True:
        page = await store.rows(table, order='id.asc', limit=str(page_size), offset=str(offset), created_at='lte.' + started)
        if owner_id is not None and any(row.get('user_id') != owner_id for row in page):
            raise HTTPException(502, 'A exportação foi interrompida por inconsistência de propriedade.')
        if len(result) + len(page) > MAX_ROWS:
            raise HTTPException(413, 'A conta excede 10.000 registros por categoria de exportação.')
        if budget is not None:
            budget[0] += len(json.dumps(page, ensure_ascii=False).encode())
            if budget[0] > MAX_BYTES:
                raise HTTPException(413, 'Exportação excede 64 MiB; reduza arquivos ou solicite suporte.')
        result.extend(page)
        # A project may enforce a lower max_rows than our requested page size.
        # Only an empty page proves the end; never silently truncate an export.
        if not page:
            return result
        offset += len(page)


async def build_export(store, directory):
    target = Path(directory) / 'CareerOS-workspace.zip'
    started = datetime.now(timezone.utc).isoformat()
    budget = [0]
    try:
        data = {'format': 'careeros-cloud-export', 'format_version': 1, 'app_version': VERSION,
                'exported_at': started, 'profile': await store.profile()}
        for table, label in [('cloud_jobs', 'jobs'), ('cloud_ai_runs', 'ai_history'), ('cloud_resumes', 'resumes')]:
            data[label] = await all_rows(store, table, started, budget, store.user.id)
        manifest = {'format_version': 1, 'app_version': VERSION, 'files': {},
                    'notice': 'Cópia da conta durante o intervalo de exportação; não é snapshot transacional nem backup de todo o servidor.'}
        with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=1) as archive:
            for row in data['resumes']:
                source = row.get('storage_path')
                pattern = re.escape(store.user.id) + r'/([0-9a-f-]{36})\.(pdf|docx)'
                match = re.fullmatch(pattern, source or '')
                if not match:
                    raise HTTPException(502, 'Referência de currículo inválida; exportação cancelada.')
                name = f'resumes/{match.group(1)}.{match.group(2)}'
                content = await store.resume_bytes(source, 5 * 1024 * 1024)
                budget[0] += len(content)
                if budget[0] > MAX_BYTES:
                    raise HTTPException(413, 'Exportação excede 64 MiB.')
                archive.writestr(name, content)
                manifest['files'][name] = hashlib.sha256(content).hexdigest()
                row['archive_path'] = name
            raw = json.dumps(data, ensure_ascii=False, indent=2).encode()
            if len(raw) + sum(info.file_size for info in archive.infolist()) > MAX_BYTES:
                raise HTTPException(413, 'Exportação excede 64 MiB.')
            manifest['files']['workspace.json'] = hashlib.sha256(raw).hexdigest()
            manifest_raw = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
            if len(raw) + len(manifest_raw) + sum(info.file_size for info in archive.infolist()) > MAX_BYTES:
                raise HTTPException(413, 'Exportação excede 64 MiB.')
            archive.writestr('workspace.json', raw)
            archive.writestr('manifest.json', manifest_raw)
        return target
    except BaseException:
        target.unlink(missing_ok=True)
        raise


@router.get('/export.zip')
async def export_account(store: SupabaseStore = Depends(get_store)):
    if _export_gate.locked():
        raise HTTPException(429, 'Outra exportação está em andamento. Tente novamente em instantes.')
    async with _export_gate:
        directory = Path(tempfile.mkdtemp(prefix='careeros-export-'))
        try:
            path = await build_export(store, directory)
            return FileResponse(path, media_type='application/zip', filename='CareerOS-workspace.zip',
                                headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'},
                                background=BackgroundTask(shutil.rmtree, directory))
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise
