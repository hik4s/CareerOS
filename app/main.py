import json,uuid,csv,io
from pathlib import Path
from fastapi import FastAPI,HTTPException,UploadFile,File
from fastapi.responses import HTMLResponse,StreamingResponse,Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.db import init_db,connect
from app.version import VERSION
from app.config import UPLOAD_DIR,MAX_PDF_BYTES
from app.models import *
from app.services.scoring import analyze
from app.services.resume import text_from_pdf,parse
from app.services.ingestion import rss,api
from app.services.providers import status,login,generate
from app.services.resume_analysis import analyze_resume,text_from_docx
from app.services.assistant import suggestions
from app.services.resume_generator import generate_docx
from app.services.learning import record as record_event,report as learning_report
from app.services.email_import import parse_eml
from app.services.agent_orchestrator import route,estimate_tokens
from app.services.security import set_secret,get_secret,redact
from app.services.event_tracker import track,track_stage,set_attribution,learning_snapshot
app=FastAPI(title='Career OS',version=VERSION);app.add_middleware(CORSMiddleware,allow_origin_regex=r'chrome-extension://.*',allow_methods=['*'],allow_headers=['*']);app.mount('/static',StaticFiles(directory='app/static'),name='static')
@app.on_event('startup')
def startup():init_db()
def profile(c):
 r=c.execute('SELECT data FROM profile WHERE id=1').fetchone();return json.loads(r['data']) if r else None
def jdecode(r):
 d=dict(r)
 for k in ['benefits','analysis']:
  try:d[k]=json.loads(d[k])
  except:pass
 return d
def add_job(c,d):
 try:
  cur=c.execute('INSERT INTO jobs(title,company,url,location,work_model,description,salary_min,benefits,source,external_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(d['title'],d['company'],d.get('url',''),d.get('location',''),d.get('work_model',''),d['description'],d.get('salary_min'),json.dumps(d.get('benefits',[]),ensure_ascii=False),d.get('source','manual'),d.get('external_id','')));return cur.lastrowid
 except:return None
@app.get('/',response_class=HTMLResponse)
def home():return Path('app/static/index.html').read_text(encoding='utf-8')
@app.get('/api/health')
def health():return {'status':'ok','version':VERSION}
@app.get('/api/profile')
def get_profile():
 with connect() as c:return profile(c)
@app.put('/api/profile')
def put_profile(p:ProfileIn):
 with connect() as c:c.execute("INSERT INTO profile(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP",(p.model_dump_json(),))
 return {'ok':True}
@app.post('/api/resume/upload')
async def upload(file:UploadFile=File(...)):
 data=await file.read(MAX_PDF_BYTES+1)
 if len(data)>MAX_PDF_BYTES:raise HTTPException(413,'PDF muito grande')
 if not data.startswith(b'%PDF'):raise HTTPException(415,'Arquivo inválido')
 try:text=text_from_pdf(data);found=parse(text)
 except Exception as e:raise HTTPException(422,'PDF sem texto selecionável') from e
 with connect() as c:
  p=profile(c) or ProfileIn().model_dump()
  for k,v in found.items():
   if k=='skills':p[k]=sorted(set(p.get(k,[])+v))
   elif v:p[k]=v
  name='resume-'+uuid.uuid4().hex+'.pdf';(UPLOAD_DIR/name).write_bytes(data);c.execute("INSERT INTO profile(id,data,resume_file,resume_text) VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,resume_file=excluded.resume_file,resume_text=excluded.resume_text",(json.dumps(p,ensure_ascii=False),name,text))
 return {'parsed':found,'review_required':True}
@app.post('/api/jobs')
def create(j:JobIn):
 with connect() as c:
  jid=add_job(c,j.model_dump())
  if not jid:raise HTTPException(409,'Duplicada')
  set_attribution(c,jid,source=j.source or 'manual')
  track(c,jid,'captured',j.source or 'manual',{'method':'manual'},f'{jid}:captured')
 return {'id':jid}
@app.post('/api/import/browser')
def browser(j:JobIn):
 with connect() as c:
  d=j.model_dump();d['source']='browser-extension';jid=add_job(c,d)
  if not jid:raise HTTPException(409,'Esta vaga já foi capturada')
  set_attribution(c,jid,source='browser-extension')
  track(c,jid,'captured','browser-extension',{'url':d.get('url')},f'{jid}:captured')
  p=profile(c)
  if p:
   a=analyze(p,d);c.execute('UPDATE jobs SET fit_score=?,analysis=? WHERE id=?',(a['score'],json.dumps(a,ensure_ascii=False),jid))
 return {'ok':True,'id':jid}
@app.get('/api/jobs')
def jobs():
 with connect() as c:return [jdecode(r) for r in c.execute('SELECT * FROM jobs ORDER BY fit_score DESC,created_at DESC')]
@app.post('/api/jobs/{jid}/analyze')
def score(jid:int):
 with connect() as c:
  p=profile(c);r=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
  if not p or not r:raise HTTPException(404,'Dados ausentes')
  j=jdecode(r);a=analyze(p,j);c.execute('UPDATE jobs SET fit_score=?,analysis=? WHERE id=?',(a['score'],json.dumps(a,ensure_ascii=False),jid));return a
@app.post('/api/jobs/{jid}/materials')
def material(jid:int):
 with connect() as c:
  p=profile(c);j=jdecode(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone());n=c.execute("SELECT value FROM settings WHERE key='ai_provider'").fetchone()['value'];a=j.get('analysis') or analyze(p,j);out=generate(n,p,j,a)
  for k in ['summary','cover_letter']:c.execute('INSERT INTO materials(job_id,kind,content,provider) VALUES(?,?,?,?)',(jid,k,out[k],out['provider']))
  return out
@app.put('/api/jobs/{jid}/stage')
def stage(jid:int,s:StageIn):
 if s.stage not in {'new','review','ready','applied','interview','offer','rejected','archived'}:raise HTTPException(400,'Etapa inválida')
 with connect() as c:
  row=c.execute('SELECT status FROM jobs WHERE id=?',(jid,)).fetchone()
  if not row:raise HTTPException(404,'Vaga não encontrada')
  previous=row['status'];c.execute('UPDATE jobs SET status=? WHERE id=?',(s.stage,jid));tracked=track_stage(c,jid,s.stage,previous)
 return {'ok':True,'event_tracked':tracked,'learning_updated':tracked}
@app.post('/api/sources')
def source(s:SourceIn):
 with connect() as c:cur=c.execute('INSERT INTO sources(name,kind,url,config) VALUES(?,?,?,?)',(s.name,s.kind,s.url,json.dumps(s.config)));return {'id':cur.lastrowid}
@app.get('/api/sources')
def sources():
 with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM sources ORDER BY id DESC')]
@app.post('/api/sources/{sid}/run')
def run_source(sid:int):
 with connect() as c:
  s=dict(c.execute('SELECT * FROM sources WHERE id=?',(sid,)).fetchone());cfg=json.loads(s['config']);items=rss(s['url'],s['name']) if s['kind']=='rss' else api(s['url'],s['name'],cfg);created=sum(bool(add_job(c,x)) for x in items);c.execute('UPDATE sources SET last_status=?,last_run_at=CURRENT_TIMESTAMP WHERE id=?',(f'{created} novas de {len(items)}',sid));return {'created':created,'received':len(items)}
@app.get('/api/metrics')
def metrics():
 with connect() as c:
  t=dict(c.execute("SELECT COUNT(*) discovered,SUM(status='applied') applied,SUM(status='interview') interviews,SUM(status='offer') offers,AVG(fit_score) avg_score FROM jobs").fetchone());t={k:v or 0 for k,v in t.items()};t['blocked']=c.execute("SELECT COUNT(*) n FROM jobs WHERE analysis LIKE '%blockers%Exige%' ").fetchone()['n'];t['interview_rate']=round(100*t['interviews']/t['applied'],1) if t['applied'] else 0;f=[dict(r) for r in c.execute('SELECT status,COUNT(*) count FROM jobs GROUP BY status')];src=[dict(r) for r in c.execute('SELECT source,COUNT(*) jobs FROM jobs GROUP BY source')];return {'totals':t,'funnel':f,'by_source':src}
@app.get('/api/provider')
def get_provider():
 with connect() as c:n=c.execute("SELECT value FROM settings WHERE key='ai_provider'").fetchone()['value']
 return {'selected':n,'providers':{x:status(x) for x in ['heuristic','codex','claude']}}
@app.put('/api/provider')
def set_provider(p:ProviderIn):
 with connect() as c:c.execute("UPDATE settings SET value=? WHERE key='ai_provider'",(p.provider,))
 return {'ok':True}
@app.post('/api/provider/{name}/connect')
def connect_provider(name:str):
 if name not in {'codex','claude'}:raise HTTPException(400,'Inválido')
 return login(name)

@app.post('/api/resume/analyze')
async def analyze_resume_file(file:UploadFile=File(...),job_id:int|None=None):
 data=await file.read(MAX_PDF_BYTES+1)
 if len(data)>MAX_PDF_BYTES:raise HTTPException(413,'Arquivo muito grande')
 name=(file.filename or '').lower()
 try:
  text=text_from_pdf(data) if name.endswith('.pdf') else text_from_docx(data) if name.endswith('.docx') else None
  if text is None:raise HTTPException(415,'Envie PDF ou DOCX')
 except HTTPException:raise
 except Exception as e:raise HTTPException(422,'Não foi possível ler o currículo') from e
 with connect() as c:
  job=jdecode(c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()) if job_id else None
  report=analyze_resume(text,job);c.execute('INSERT INTO resume_analyses(filename,job_id,overall_score,ats_score,structure_score,content_score,match_score,report) VALUES(?,?,?,?,?,?,?,?)',(file.filename,job_id,report['overall_score'],report['ats_score'],report['structure_score'],report['content_score'],report['match_score'],json.dumps(report,ensure_ascii=False)))
 return report
@app.get('/api/answers')
def answers():
 with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM answer_bank ORDER BY category,question_key')]
@app.post('/api/answers')
def answer_create(payload:dict):
 if not payload.get('question_key') or not payload.get('answer'):raise HTTPException(422,'Chave e resposta obrigatórias')
 with connect() as c:
  cur=c.execute('INSERT INTO answer_bank(question_key,question_pattern,answer,category) VALUES(?,?,?,?)',(payload['question_key'],payload.get('question_pattern',''),payload['answer'],payload.get('category','general')));return {'id':cur.lastrowid}
@app.put('/api/answers/{aid}')
def answer_update(aid:int,payload:dict):
 with connect() as c:c.execute('UPDATE answer_bank SET answer=?,question_pattern=?,category=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(payload.get('answer',''),payload.get('question_pattern',''),payload.get('category','general'),aid))
 return {'ok':True}
@app.post('/api/assistant/suggest')
def assistant_suggest(payload:dict):
 with connect() as c:return suggestions(c,payload.get('questions',[]))

@app.get('/api/agents/plan')
def agent_plan():
 with connect() as c:provider=c.execute("SELECT value FROM settings WHERE key='ai_provider'").fetchone()['value']
 return {'provider':provider,'routes':{x:route(x,provider) for x in ['extract','classify','score','write','review','strategy']},'policy':'Determinístico primeiro; economia para extração/classificação; balanceado para escrita/revisão; premium somente para estratégia solicitada.'}
@app.post('/api/jobs/{jid}/resume.docx')
def generate_resume(jid:int,variant:str='A'):
 with connect() as c:
  p=profile(c);row=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
  if not p or not row:raise HTTPException(404,'Perfil ou vaga ausente')
  j=jdecode(row);a=j.get('analysis') or analyze(p,j);data=generate_docx(p,j,a);filename=f"curriculo-{jid}-{variant}.docx";path=UPLOAD_DIR/filename;path.write_bytes(data);cur=c.execute('INSERT INTO resume_versions(job_id,name,skills,experience,docx_path,variant) VALUES(?,?,?,?,?,?)',(jid,filename,json.dumps(a.get('matched_skills',[])),json.dumps(p.get('evidence',[]),ensure_ascii=False),str(path),variant));set_attribution(c,jid,variant,cur.lastrowid);track(c,jid,'resume_generated','resume-agent',{'variant':variant,'resume_version_id':cur.lastrowid},f'{jid}:resume:{cur.lastrowid}')
 return Response(data,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',headers={'Content-Disposition':f'attachment; filename="{filename}"'})
@app.post('/api/experiments')
def experiment_create(payload:dict):
 with connect() as c:cur=c.execute('INSERT INTO experiments(name,kind,control_variant) VALUES(?,?,?)',(payload.get('name','Experimento'),payload.get('kind','resume'),payload.get('control_variant','A')));return {'id':cur.lastrowid}
@app.post('/api/experiments/{eid}/events')
def experiment_event(eid:int,payload:dict):
 with connect() as c:record_event(c,eid,payload.get('job_id'),payload.get('variant','A'),payload.get('event_type','view'),payload.get('metadata'));return {'ok':True}
@app.get('/api/learning')
def learning():
 with connect() as c:return {'experiments':learning_report(c),'live':learning_snapshot(c),'storage':'sqlite-local','recommendation':'Só promover uma variante após volume suficiente; não concluir causalidade com amostras pequenas.'}
@app.post('/api/followups')
def followup_create(payload:dict):
 with connect() as c:cur=c.execute('INSERT INTO followups(job_id,due_at,channel,template,notes) VALUES(?,?,?,?,?)',(payload.get('job_id'),payload.get('due_at'),payload.get('channel','email'),payload.get('template','Olá, gostaria de acompanhar o andamento da minha candidatura.'),payload.get('notes','')));return {'id':cur.lastrowid}
@app.get('/api/followups')
def followups():
 with connect() as c:return [dict(r) for r in c.execute("SELECT f.*,j.title,j.company FROM followups f LEFT JOIN jobs j ON j.id=f.job_id ORDER BY f.due_at")]
@app.put('/api/followups/{fid}')
def followup_update(fid:int,payload:dict):
 with connect() as c:c.execute('UPDATE followups SET status=?,notes=? WHERE id=?',(payload.get('status','done'),payload.get('notes',''),fid))
 return {'ok':True}
@app.post('/api/email/import')
async def email_import(files:list[UploadFile]=File(...)):
 imported=[]
 with connect() as c:
  for f in files:
   item=parse_eml(await f.read());mid=item['message_id'] or f.filename
   try:
    c.execute('INSERT INTO email_imports(message_id,sender,subject,received_at,body,classification) VALUES(?,?,?,?,?,?)',(mid,item['sender'],item['subject'],item['received_at'],item['body'],item['classification']))
    hay=(item['subject']+' '+item['body']).lower();matches=[dict(r) for r in c.execute('SELECT id,title,company FROM jobs') if (r['company'] and r['company'].lower() in hay) or (r['title'] and r['title'].lower() in hay)]
    if len(matches)==1 and item['classification'] in {'interview','rejected','application'}:
     job=matches[0];event='applied' if item['classification']=='application' else item['classification'];track(c,job['id'],event,'email',{'message_id':mid,'subject':item['subject']},f"{job['id']}:email:{mid}:{event}");c.execute('UPDATE jobs SET status=? WHERE id=?',(event if event!='application' else 'applied',job['id']))
    imported.append(item)
   except:pass
 return {'imported':len(imported),'messages':imported}
@app.get('/api/email/imports')
def email_imports():
 with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM email_imports ORDER BY id DESC LIMIT 100')]
@app.post('/api/security/secret')
def secret_set(payload:dict):
 if not payload.get('name') or not payload.get('value'):raise HTTPException(422,'Nome e valor obrigatórios')
 try:set_secret(payload['name'],payload['value']);return {'ok':True,'stored_in':'system_keyring'}
 except Exception as e:raise HTTPException(503,'Cofre do sistema indisponível') from e
@app.get('/api/security/status')
def security_status():
 try:
  import keyring;backend=keyring.get_keyring().__class__.__name__;available=True
 except Exception:
  backend='unavailable';available=False
 return {'keyring_available':available,'keyring_backend':backend,'data_directory':str(UPLOAD_DIR.parent),'events_storage':'sqlite-local','redaction_enabled':True,'secrets_in_database':False}
@app.get('/api/onboarding')
def onboarding():
 with connect() as c:
  p=profile(c) or {};jobs=c.execute('SELECT COUNT(*) n FROM jobs').fetchone()['n'];answers=c.execute('SELECT COUNT(*) n FROM answer_bank').fetchone()['n']
 return {'profile_complete':bool(p.get('email') and p.get('github')),'resume_loaded':bool(p.get('skills')),'jobs_captured':jobs,'answer_bank':answers,'next_action':'Complete e-mail e GitHub' if not p.get('email') else 'Capture uma vaga' if not jobs else 'Gere currículo por vaga'}
@app.get('/api/platforms')
def platforms():return [{'name':'Gupy','url':'https://portal.gupy.io/job-search/term=estagio%20tecnologia'},{'name':'Indeed','url':'https://br.indeed.com/jobs?q=estagio+ti+python+automacao&l=Remoto'},{'name':'LinkedIn','url':'https://www.linkedin.com/jobs/search/?keywords=estagio%20desenvolvimento%20python&location=Brasil&f_WT=2'},{'name':'Vagas.com','url':'https://www.vagas.com.br/vagas-de-estagio-em-tecnologia'},{'name':'Inova Prudente','url':'https://inovaprudente.com.br/vagas'},{'name':'CIEE','url':'https://portal.ciee.org.br/'}]
@app.get('/api/export.csv')
def export():
 with connect() as c:rows=c.execute('SELECT company,title,url,fit_score,status,source FROM jobs').fetchall()
 o=io.StringIO();w=csv.writer(o);w.writerow(['company','title','url','fit_score','status','source']);w.writerows([tuple(r) for r in rows]);return StreamingResponse(iter([o.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=career_os.csv'})
