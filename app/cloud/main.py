"""Cloud-only entry point: uvicorn app.cloud.main:app."""
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
from zipfile import ZipFile, BadZipFile
import re
import json
import asyncio
import subprocess
import sys
import httpx
from typing import Annotated, Literal
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.services.scoring import analyze
from .config import settings
from .discovery import discovery_lifespan, router as discovery_router
from .store import SupabaseStore, get_store
from .version import VERSION

app = FastAPI(title='CareerOS Cloud', version=VERSION, lifespan=discovery_lifespan)
_parse_gate = asyncio.Semaphore(1)
app.add_middleware(CORSMiddleware, allow_origins=list(settings().cors_origins), allow_origin_regex=r'chrome-extension://[a-p]{32}', allow_credentials=False, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])

def response_privacy_headers(request):
    headers = {'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'}
    if request.url.path.startswith('/api/'):
        headers['Cache-Control'] = 'no-store'
    return headers

@app.middleware('http')
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers.update(response_privacy_headers(request))
    return response

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    # Starlette creates these responses outside user middleware.
    return JSONResponse(status_code=500, content={'detail': 'Não foi possível concluir a operação. Tente novamente em instantes.'},
                        headers=response_privacy_headers(request))

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'detail': [{'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]})

@app.get('/api/config')
async def config():
    cfg = settings()
    return {'configured': cfg.configured, 'supabase_url': cfg.supabase_url, 'supabase_anon_key': cfg.supabase_anon_key, 'version': VERSION}

@app.get('/api/health')
async def health():
    return {'status': 'ok', 'configured': settings().configured, 'version': VERSION}

@app.get('/api/auth/providers')
async def auth_providers():
    cfg = settings()
    if not cfg.configured:
        return {'ready': False, 'providers': [], 'reason': 'configuration_missing'}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(cfg.supabase_url + '/auth/v1/settings', headers={'apikey': cfg.supabase_anon_key})
        response.raise_for_status()
        external = response.json().get('external') or {}
        providers = [name for name in ('google', 'github') if external.get(name) is True]
        return {'ready': bool(providers), 'providers': providers,
                'reason': None if providers else 'oauth_setup_required'}
    except (httpx.HTTPError, ValueError):
        return {'ready': False, 'providers': [], 'reason': 'auth_unavailable'}

JobStatus = Literal['saved', 'new', 'ready', 'applied', 'interview', 'offer', 'rejected', 'review', 'skip', 'archived', 'screening', 'assessment', 'withdrawn', 'accepted']
ShortText = Annotated[str, Field(max_length=500)]

class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    full_name: ShortText = ''
    email: ShortText = ''
    phone: ShortText = ''
    city: ShortText = ''
    course: ShortText = ''
    term: int = Field(default=1, ge=1, le=20)
    graduation_date: ShortText = ''
    linkedin: ShortText = ''
    github: ShortText = ''
    avatar: str = Field(default='', max_length=50000, pattern=r'^(data:image/jpeg;base64,[A-Za-z0-9+/]+={0,2})?$')
    summary: str = Field(default='', max_length=10000)
    target_roles: list[ShortText] = Field(default_factory=list, max_length=50)
    skills: list[ShortText] = Field(default_factory=list, max_length=100)
    evidence: list[dict[str, str]] = Field(default_factory=list, max_length=50)
    preferences: dict[str, str | bool | list[ShortText]] = Field(default_factory=dict, max_length=30)

    @model_validator(mode='after')
    def bounded_json(self):
        if len(json.dumps(self.model_dump(), ensure_ascii=False).encode()) > 100000:
            raise ValueError('Profile exceeds 100000 bytes')
        if any(len(item) > 20 or any(len(k) > 100 or len(v) > 10000 for k, v in item.items()) for item in self.evidence):
            raise ValueError('Evidence exceeds size limits')
        return self

class JobURLMixin(BaseModel):
    @field_validator('url', check_fields=False)
    @classmethod
    def safe_url(cls, value):
        if value in ('', None):
            return value
        try:
            parts = urlsplit(value)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or any(ord(c) < 32 for c in value):
                raise ValueError()
            parts.port
        except ValueError:
            raise ValueError('URL must be an HTTP or HTTPS address without credentials') from None
        return value

class JobInput(JobURLMixin):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=500)
    company: str = Field(default='', max_length=500)
    description: str = Field(default='', max_length=100000)
    url: str = Field(default='', max_length=4096)
    location: str = Field(default='', max_length=500)
    work_model: str = Field(default='', max_length=100)
    status: JobStatus = 'saved'

class JobPatch(JobURLMixin):
    model_config = ConfigDict(extra='forbid')
    title: str | None = Field(default=None, min_length=1, max_length=500)
    company: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=100000)
    url: str | None = Field(default=None, max_length=4096)
    location: str | None = Field(default=None, max_length=500)
    work_model: str | None = Field(default=None, max_length=100)
    status: JobStatus | None = None

@app.get('/api/profile')
async def profile(store: SupabaseStore = Depends(get_store)):
    return await store.profile()

@app.put('/api/profile')
async def save_profile(data: ProfileInput, store: SupabaseStore = Depends(get_store)):
    return await store.save_profile(data.model_dump())

class AccountDeletion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirmation: Literal['EXCLUIR']


@app.post('/api/account/delete', status_code=204)
async def delete_account(data: AccountDeletion, store: SupabaseStore = Depends(get_store)):
    cfg = store.config
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            result = await client.post(
                cfg.supabase_url + '/functions/v1/delete-account',
                headers={'apikey': cfg.supabase_anon_key, 'Authorization': 'Bearer ' + store.user.token},
                json=data.model_dump(),
            )
    except httpx.HTTPError:
        raise HTTPException(503, 'Não foi possível confirmar a exclusão. Tente novamente.') from None
    if result.status_code == 401:
        raise HTTPException(401, 'Entre novamente para excluir sua conta.')
    if result.status_code != 204:
        raise HTTPException(502, 'Não foi possível concluir a exclusão. Tente novamente.')
    return Response(status_code=204)


@app.get('/api/jobs')
async def jobs(store: SupabaseStore = Depends(get_store)):
    return await store.jobs()

@app.post('/api/jobs', status_code=201)
async def create_job(data: JobInput, store: SupabaseStore = Depends(get_store)):
    return await store.create_job(data.model_dump())

@app.get('/api/jobs/{id}')
async def job(id: UUID, store: SupabaseStore = Depends(get_store)):
    return await store.job(id)

@app.patch('/api/jobs/{id}')
async def update_job(id: UUID, data: JobPatch, store: SupabaseStore = Depends(get_store)):
    return await store.update_job(id, data.model_dump(exclude_unset=True, exclude_none=True))

@app.delete('/api/jobs/{id}', status_code=204)
async def delete_job(id: UUID, store: SupabaseStore = Depends(get_store)):
    await store.delete_job(id)
    return Response(status_code=204)

@app.post('/api/jobs/{id}/analyze')
async def analyze_job(id: UUID, store: SupabaseStore = Depends(get_store)):
    row, profile = await store.job(id), await store.profile()
    try:
        validated_profile = ProfileInput.model_validate(profile).model_dump()
    except ValueError:
        raise HTTPException(422, 'Stored profile needs review before analysis') from None
    result = analyze(validated_profile, row)
    result.update({'method': 'skills_heuristic', 'note': 'Skill overlap only; review the job and your actual experience.'})
    return await store.update_job(id, {'fit_score': result['score'], 'analysis': result})

@app.get('/api/metrics')
async def metrics(store: SupabaseStore = Depends(get_store)):
    jobs = await store.jobs()
    statuses = {}
    for row in jobs:
        state = row.get('status', 'saved')
        statuses[state] = statuses.get(state, 0) + 1
    return {'total_jobs': len(jobs), 'by_status': statuses}

@app.get('/api/resumes')
async def resumes(store: SupabaseStore = Depends(get_store)):
    return await store.rows('cloud_resumes', select='id,filename,created_at', order='created_at.desc')

@app.post('/api/resumes', status_code=201)
async def upload_resume(file: UploadFile = File(...), store: SupabaseStore = Depends(get_store)):
    ext = Path(file.filename or '').suffix.lower()
    if ext not in ('.pdf', '.docx'):
        raise HTTPException(400, 'Upload a PDF or DOCX resume')
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, 'Resume must be at most 5 MiB')
    if len(await store.rows('cloud_resumes', limit='10')) >= 10:
        raise HTTPException(409, 'Maximum of 10 resumes reached')
    if ext == '.docx':
        try:
            with ZipFile(BytesIO(content)) as archive:
                if sum(entry.file_size for entry in archive.infolist()) > 25 * 1024 * 1024:
                    raise HTTPException(413, 'Expanded document is too large')
        except BadZipFile:
            raise HTTPException(400, 'Resume could not be parsed') from None
    if _parse_gate.locked():
        raise HTTPException(429, 'Outro documento está sendo processado. Aguarde alguns segundos.')
    async with _parse_gate:
        try:
            parsed = await asyncio.to_thread(subprocess.run,
                [sys.executable, '-m', 'app.cloud.resume_parser', ext], input=content,
                capture_output=True, timeout=15, cwd=str(Path(__file__).resolve().parents[2]))
            if parsed.returncode:
                raise ValueError('Parse failed')
            text = json.loads(parsed.stdout)['text']
        except (subprocess.TimeoutExpired, ValueError, KeyError, OSError):
            raise HTTPException(422, 'Não foi possível ler o currículo. Use PDF/DOCX com até 30 páginas e texto selecionável.') from None
    rid = str(uuid4())
    path = f'{store.user.id}/{rid}{ext}'
    await store.request('POST', '/storage/v1/object/career-resumes/' + path, content=content, headers={'Content-Type': 'application/pdf' if ext == '.pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'})
    try:
        return await store.insert('cloud_resumes', {'id': rid, 'filename': Path(file.filename).name[:255], 'storage_path': path, 'text': text})
    except Exception:
        await store.request('DELETE', '/storage/v1/object/career-resumes', json={'prefixes': [path]})
        raise

async def resume_row(id, store):
    rows = await store.rows('cloud_resumes', id='eq.' + str(id), limit='1')
    if not rows:
        raise HTTPException(404, 'Resume not found')
    return rows[0]

@app.get('/api/resumes/{id}/sections')
async def resume_sections(id: UUID, store: SupabaseStore = Depends(get_store)):
    from app.services.resume_analysis import analyze_resume

    row = await resume_row(id, store)
    text = row.get('text') or ''
    report = analyze_resume(text[:100000])
    return {'has_text': bool(text.strip()), 'sections': report['sections'], 'contacts': report['contacts']}


@app.get('/api/resumes/{id}/profile-preview')
async def resume_profile_preview(id: UUID, store: SupabaseStore = Depends(get_store)):
    from .profile_import import profile_suggestions

    row = await resume_row(id, store)
    text = row.get('text') or ''
    return {'has_text': bool(text.strip()), 'suggestions': profile_suggestions(text)}


@app.get('/api/resumes/{id}/download')
async def download_resume(id: UUID, store: SupabaseStore = Depends(get_store)):
    row = await resume_row(id, store)
    result = await store.request('POST', '/storage/v1/object/sign/career-resumes/' + row['storage_path'], json={'expiresIn': 60})
    signed = result.get('signedURL') or result.get('signedUrl')
    if not isinstance(signed, str):
        raise HTTPException(502, 'Download link could not be created')
    return {'url': store.config.supabase_url + '/storage/v1' + signed if signed.startswith('/') else signed, 'expires_in': 60}

@app.delete('/api/resumes/{id}', status_code=204)
async def delete_resume(id: UUID, store: SupabaseStore = Depends(get_store)):
    row = await resume_row(id, store)
    await store.request('DELETE', '/storage/v1/object/career-resumes', json={'prefixes': [row['storage_path']]})
    await store.request('DELETE', '/rest/v1/cloud_resumes', params={'user_id': 'eq.' + store.user.id, 'id': 'eq.' + str(id)})
    return Response(status_code=204)

STATIC = Path(__file__).resolve().parent / 'static'
from .ai import router as ai_router
app.include_router(ai_router)
from .export import router as export_router
app.include_router(export_router)
app.include_router(discovery_router)

@app.get('/api/extension.zip')
async def extension_download():
    root = Path(__file__).resolve().parents[2] / 'extension-cloud'
    output = BytesIO()
    with ZipFile(output, 'w') as archive:
        for file in sorted(root.iterdir()):
            if file.is_file():
                archive.writestr(file.name, file.read_bytes())
    return Response(output.getvalue(), media_type='application/zip',
                    headers={'Content-Disposition': 'attachment; filename="CareerOS-Extensao.zip"'})

if STATIC.exists():
    app.mount('/static', StaticFiles(directory=STATIC), name='static')

@app.get('/auth', include_in_schema=False)
@app.get('/')
async def home():
    if (STATIC / 'index.html').exists():
        return FileResponse(STATIC / 'index.html')
    return {'name': 'CareerOS Cloud', 'configured': settings().configured}
