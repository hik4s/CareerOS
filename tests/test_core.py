import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from app.services.scoring import analyze
from app.services.resume import parse
from app.services.ingestion import clean,norm,pick

def test_semester_blocker():
 r=analyze({'term':2,'skills':['python'],'evidence':[]},{'title':'Estágio','description':'A partir do 4º semestre. Python'})
 assert r['required_term']==4 and r['blockers'] and r['recommendation']=='skip'
def test_good_score():
 r=analyze({'term':2,'skills':['python','playwright','sql','git'],'evidence':[{'name':'x'}]},{'title':'Estágio automação','description':'Python Playwright SQL Git'})
 assert r['score']>=65
def test_resume():
 x=parse('Kauan Inacio dos Santos\nkauan@example.com\n2º termo\nPython Playwright SQL GitHub\nhttps://github.com/kauan')
 assert x['full_name']=='Kauan Inacio dos Santos' and x['term']==2 and 'python' in x['skills']
def test_clean():assert clean('<b>A &amp; B</b>')=='A & B'
def test_norm():assert norm({'title':'Dev','link':'https://x'},'rss')['external_id']
def test_pick():assert pick({'a':{'b':2}},'a.b')==2
from app.services.resume_analysis import analyze_resume
from app.services.assistant import DEFAULTS

def test_resume_analysis_general():
 text='''Kauan Inacio dos Santos\nkauan@example.com | 18 99999-0000\nResumo profissional\nEstudante de TI com Python.\nProjetos\nDesenvolvi e automatizei processos com Python e Playwright, reduzindo 30% do trabalho manual.\nFormação\nBacharelado em Tecnologia da Informação\nHabilidades\nPython, Playwright, SQL, Git\nhttps://github.com/kauan'''
 r=analyze_resume(text);assert r['overall_score']>60 and r['structure_score']>=70 and r['strengths']
def test_resume_analysis_job_match():
 r=analyze_resume('Python SQL Git projeto automação',{'title':'Estágio Python','description':'Python SQL Docker'});assert r['match_score']>0 and 'docker' in r['missing_keywords']
def test_answer_defaults():assert len(DEFAULTS)>=5 and all(len(x)==4 for x in DEFAULTS)
def test_long_resume_warning():
 r=analyze_resume(('palavra '*1000));assert any('Reduzir' in x for x in r['improvements'])
from app.services.agent_orchestrator import route,estimate_tokens
from app.services.email_import import parse_eml
from app.services.security import redact
from app.services.resume_generator import generate_docx

def test_agent_economy_routing():
 assert route('extract','codex')['tier']=='economy';assert route('strategy','claude')['tier']=='premium';assert estimate_tokens('abcd'*10)==10
def test_email_classification_interview():
 raw=b'Subject: Entrevista para Estagio\nFrom: rh@example.com\nMessage-ID: <1@test>\n\nGostariamos de agendar uma entrevista.'
 assert parse_eml(raw)['classification']=='interview'
def test_redaction():
 x=redact('kauan@example.com api_key=secret');assert '[EMAIL]' in x and '[REDACTED]' in x
def test_resume_generator_docx():
 data=generate_docx({'full_name':'Kauan','course':'TI','term':2,'skills':['python'],'evidence':[{'name':'Projeto','description':'Automacao'}]},{'title':'Desenvolvimento','company':'X'},{'matched_skills':['python']});assert data[:2]==b'PK' and len(data)>1000
from app.services.event_tracker import track,track_stage,set_attribution,learning_snapshot
from app.db import init_db,connect

def test_event_tracker_updates_learning(tmp_path,monkeypatch):
 import app.db as db
 monkeypatch.setattr(db,'DB_PATH',tmp_path/'events.db');db.init_db()
 with db.connect() as c:
  jid=c.execute("INSERT INTO jobs(title,company,description) VALUES('Estagio Python','ACME','Python')").lastrowid
  set_attribution(c,jid,'B',source='test')
  assert track(c,jid,'captured','test',{},f'{jid}:captured')
  assert track_stage(c,jid,'applied','new')
  assert track_stage(c,jid,'interview','applied')
  snap=learning_snapshot(c)
  assert snap['totals']['applied']==1 and snap['totals']['interview']==1
  assert snap['variants'][0]['variant']=='B' and snap['variants'][0]['interview_rate']==100.0

def test_stage_event_is_idempotent(tmp_path,monkeypatch):
 import app.db as db
 monkeypatch.setattr(db,'DB_PATH',tmp_path/'idem.db');db.init_db()
 with db.connect() as c:
  jid=c.execute("INSERT INTO jobs(title,company,description) VALUES('Estagio','X','TI')").lastrowid
  assert track_stage(c,jid,'applied','new')
  assert not track_stage(c,jid,'applied','applied')
  assert c.execute("SELECT COUNT(*) n FROM analytics_events WHERE event_type='applied'").fetchone()['n']==1
