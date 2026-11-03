"""Credential lifetime, destination, and package contract for the cloud extension."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / 'extension-cloud'


def node(script):
    if not shutil.which('node'):
        pytest.skip('Node is required for extension JavaScript contract tests')
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_permissions_and_packaged_scripts():
    manifest = json.loads((EXT / 'manifest.json').read_text())
    assert manifest['manifest_version'] == 3
    assert set(manifest['permissions']) == {'activeTab', 'scripting', 'storage'}
    assert not manifest.get('host_permissions')
    assert not manifest.get('content_scripts')
    assert 'https://*/*' in manifest['optional_host_permissions']
    assert '<all_urls>' not in manifest['optional_host_permissions']
    assert (EXT / manifest['background']['service_worker']).is_file()
    assert (EXT / manifest['action']['default_popup']).is_file()
    assert 'http://' not in (EXT / 'popup.html').read_text()


def test_origin_validation():
    node(r"""
const assert=require('node:assert/strict');
const {careerOrigin}=require('./extension-cloud/origin.js');
for (const origin of ['https://career.example', 'https://career.example:8443', 'http://localhost:8000', 'http://127.0.0.1:8000','http://[::1]:8000']) assert.equal(careerOrigin(origin),origin);
for (const invalid of ['http://career.example','https://user:secret@career.example','https://career.example/path','https://career.example/?token=secret','https://career.example/#token','javascript:alert(1)','file:///tmp/a','http://localhost.evil.example','http://127.0.0.2:8000','']) assert.throws(()=>careerOrigin(invalid));
""")


def test_capture_uses_origin_bound_session_and_clears_expired_token():
    node(r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const session={careerToken:'account-token',careerTokenOrigin:'https://career.example'};
let captures=0,requests=0;
const context={URL,importScripts:()=>{},chrome:{runtime:{id:'self',onMessage:{addListener:()=>{}}},storage:{local:{get:async()=>({careerOrigin:'https://career.example'})},session:{get:async()=>session,remove:async keys=>keys.forEach(k=>delete session[k])}},permissions:{contains:async()=>true},scripting:{executeScript:async()=>{captures++;return [{result:{title:'Engineer',company:'Example',description:'Job details',url:'https://jobs.example/1',benefits:['not in cloud model']}}]}}},fetch:async(url,options)=>{requests++;assert.equal(url,'https://career.example/api/jobs');assert.equal(options.headers.Authorization,'Bearer account-token');assert.equal(options.redirect,'error');const job=JSON.parse(options.body);assert.equal(job.title,'Engineer');assert.equal(job.status,'saved');assert.equal(job.benefits,undefined);return {ok:false,status:401};}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('extension-cloud/origin.js','utf8')+'\n'+fs.readFileSync('extension-cloud/background.js','utf8'),context);
(async()=>{
 session.careerTokenOrigin='https://other.example';
 assert.equal((await context.capture(1)).ok,false);assert.equal(requests,0);assert.equal(captures,0);
 session.careerTokenOrigin='https://career.example';
 const response=await context.capture(1);assert.equal(response.ok,false);assert.equal(requests,1);assert.equal(session.careerToken,undefined);assert.equal(session.careerTokenOrigin,undefined);
})().catch(e=>{console.error(e);process.exitCode=1});
""")


def test_cloud_runtime_is_separate():
    requirements=(ROOT/'requirements-cloud.txt').read_text().lower()
    assert all(name not in requirements for name in ['keyring>=', 'pyinstaller>=', 'msal>=', 'pytest>='])
    render=(ROOT/'render.yaml').read_text()
    assert 'uvicorn app.cloud.main:app --host 0.0.0.0 --port $PORT' in render
    assert 'pip install -r requirements-cloud.txt' in render
    assert 'plan: free' in render
    assert 'service_role' not in render
