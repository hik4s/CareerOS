'use strict';
// Exercises the actual loading functions without a browser or private account.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('app/cloud/static/app.js','utf8');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',classList:{toggle(){},add(){},remove(){}},setAttribute(){},removeAttribute(){}});return elements.get(id)}
const context=vm.createContext({document:{getElementById:element},performance:{now:()=>0},setTimeout,clearTimeout,console});
vm.runInContext(source.slice(0,source.indexOf('function showSession(')),context);
vm.runInContext(`let pendingJobUpdates=new Set(),jobStageChanges=new Map(),jobMutationGeneration=0;session={user:{id:'test'}};function render(){if(!workspaceReady){if(workspaceError)$('view').innerHTML='retry';else pageLoading();}}toast=()=>{};`,context);
(async()=>{
  await vm.runInContext(`api=async path=>path==='/api/ai/history'?new Promise(()=>{}):[];reload()`,context);
  assert.equal(vm.runInContext('workspaceReady && !workspacePending',context),true,'AI history must not block the dashboard');
  await vm.runInContext(`workspaceReady=false;api=async()=>{throw Error('offline')};reload()`,context);
  assert.equal(element('view').innerHTML,'retry');
  assert.equal(vm.runInContext('workspacePending',context),false);
  await vm.runInContext(`workspaceReady=true;$('view').innerHTML='existing content';reload()`,context);
  assert.equal(element('view').innerHTML,'existing content','refresh errors retain visible data');
  await vm.runInContext(`workspaceReady=false;let resolves=[];api=()=>new Promise(resolve=>resolves.push(resolve));const old=reload();loadGeneration++;workspacePending=false;resolves.forEach(resolve=>resolve([]));old`,context);
  assert.equal(vm.runInContext('workspaceReady',context),false,'stale account responses are ignored');
  vm.runInContext('tab="overview";pageLoading()',context);
  assert(element('view').innerHTML.includes('skeleton-metrics'));
  console.log('PASS dashboard independence, retry, retained data, stale responses, page skeleton');
})().catch(error=>{console.error(error);process.exitCode=1});
