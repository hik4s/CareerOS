import asyncio
import json
from pathlib import Path
import sys
import httpx
import pytest
sys.path.insert(0, str(Path(__file__).parents[1]))
from app.cloud.ai import AIRequest, build_context, fingerprint, estimate, call_provider, execute


class Store:
    def __init__(self):
        self.runs = []
    async def profile(self):
        return {'full_name':'Pessoa', 'email':'private@example.com','skills':['Python'], 'course':'TI', 'evidence':[]}
    async def job(self, id):
        return {'title':'Estágio','description':'Python SQL','company':'ACME'}
    async def ai_cached(self, value):
        return next((r for r in self.runs if r['request_hash'] == value), None)
    async def save_ai_run(self, data):
        self.runs.append(data)


def run(coro):
    return asyncio.run(coro)


def test_context_excludes_email_and_caps_job_text():
    context = build_context({'email':'private@example.com','skills':['Python']}, {'description':'x'*80000}, AIRequest())
    assert 'private@example.com' not in json.dumps(context)
    assert len(context['job']['description']) <= 6000


def test_estimate_and_fingerprint_ignore_api_key():
    one=AIRequest(provider='openai',model='test-model',api_key='secret-one-123',input_price_per_million=1,output_price_per_million=2)
    two=one.model_copy(update={'api_key':'secret-two-456'})
    assert fingerprint(one, {'skills':['Python']}) == fingerprint(two, {'skills':['Python']})
    assert estimate(one, {'skills':['Python']})['estimated_max_cost_usd'] > 0


def test_heuristic_does_not_call_provider():
    store=Store()
    result=run(execute(AIRequest(task='summary'), store))
    assert result['provider']=='heuristic' and result['input_tokens']==0
    assert 'projeto prático' not in result['result']


def test_provider_usage_and_cache_prevent_duplicate_charge():
    requests=[]
    def respond(request):
        requests.append(request)
        return httpx.Response(200,json={'choices':[{'message':{'content':'Texto factual'}}], 'usage':{'prompt_tokens':30,'completion_tokens':10}})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            store=Store()
            payload=AIRequest(provider='openai',model='test-model',api_key='test-secret-key', task='summary')
            a=await execute(payload,store,client=client)
            b=await execute(payload,store,client=client)
            assert a['input_tokens']==30 and a['output_tokens']==10
            assert b['cached'] and b['input_tokens']==0 and b['estimated_cost_usd']==0
            assert len(requests)==1
            assert 'test-secret-key' not in json.dumps(store.runs)
            assert requests[0].url.host=='api.openai.com'
    run(scenario())


def test_bad_key_sanitized_no_retry():
    from fastapi import HTTPException
    calls=[]
    def denied(request):
        calls.append(request)
        return httpx.Response(401,json={'error':'test-secret-key'})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(denied)) as client:
            with pytest.raises(HTTPException) as error:
                await execute(AIRequest(provider='openai',model='test',api_key='test-secret-key'), Store(), client=client)
            assert 'test-secret-key' not in str(error.value.detail)
            assert len(calls)==1
    run(scenario())



@pytest.mark.parametrize('provider', ['anthropic','deepseek'])
def test_other_provider_protocols(provider):
    def respond(request):
        body=json.loads(request.content)
        assert body['max_tokens']==512
        if provider=='anthropic':
            assert request.headers['x-api-key']=='test-secret-key'
            return httpx.Response(200,json={'content':[{'type':'text','text':'Resposta'}], 'usage':{'input_tokens':40,'output_tokens':8}})
        return httpx.Response(200,json={'choices':[{'message':{'content':'Resposta'}}], 'usage':{'prompt_tokens':40,'completion_tokens':8}})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            text,usage=await call_provider(AIRequest(provider=provider, model='test',api_key='test-secret-key',max_output_tokens=512),{},client)
            assert text=='Resposta' and usage=={'input_tokens':40,'output_tokens':8}
    run(scenario())


def test_selected_resume_is_owner_scoped_and_used_locally():
    from uuid import UUID
    class ResumeStore(Store):
        async def rows(self, table, **filters):
            assert table == 'cloud_resumes'
            assert filters['id'] == 'eq.11111111-1111-1111-1111-111111111111'
            return [{'text':'Formação Python SQL Projetos automate@example.com https://private.example'}]
    result=run(execute(AIRequest(resume_id=UUID('11111111-1111-1111-1111-111111111111')), ResumeStore()))
    assert 'currículo selecionado' in result['result']
    assert result['input_tokens'] == 0
    assert 'automate@example.com' not in result['result']


def test_ai_routes_reject_unauthenticated_and_redact_invalid_key(monkeypatch):
    from fastapi.testclient import TestClient
    from app.cloud.main import app
    from app.cloud.auth import User, require_user
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY','public-anon')
    with TestClient(app) as client:
        assert client.get('/api/ai/history').status_code == 401
        assert client.post('/api/ai/run',json={}).status_code == 401
        app.dependency_overrides[require_user]=lambda: User('11111111-1111-1111-1111-111111111111',None,'token')
        try:
            response=client.post('/api/ai/run', json={'api_key':'private-marker', 'max_output_tokens':99999})
            assert response.status_code==422 and 'private-marker' not in response.text
        finally:
            app.dependency_overrides.clear()


def test_ai_cache_requests_include_user_filter(monkeypatch):
    from app.cloud.store import SupabaseStore
    from app.cloud.auth import User
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY','public-anon')
    owner='11111111-1111-1111-1111-111111111111'
    seen=[]
    def handler(request):
        seen.append(request)
        assert request.url.params['user_id']=='eq.'+owner
        assert request.url.params['request_hash']=='eq.fingerprint'
        assert request.headers['Authorization']=='Bearer owner-token'
        return httpx.Response(200,json=[])
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    assert run(SupabaseStore(User(owner,None,'owner-token')).ai_cached('fingerprint')) is None
    assert len(seen)==1
