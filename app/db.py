import sqlite3
from app.migrations import migrate
from contextlib import contextmanager
from app.config import DB_PATH
SCHEMA='''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS profile(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL,resume_file TEXT DEFAULT '',resume_text TEXT DEFAULT '',updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,company TEXT NOT NULL,url TEXT DEFAULT '',location TEXT DEFAULT '',work_model TEXT DEFAULT '',description TEXT NOT NULL,salary_min REAL,benefits TEXT DEFAULT '[]',source TEXT DEFAULT 'manual',external_id TEXT DEFAULT '',status TEXT DEFAULT 'new',fit_score REAL DEFAULT 0,analysis TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS ux_job_url ON jobs(url) WHERE url<>'';
CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,kind TEXT NOT NULL,url TEXT NOT NULL,config TEXT DEFAULT '{}',last_status TEXT DEFAULT '',last_run_at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS answer_bank(id INTEGER PRIMARY KEY AUTOINCREMENT,question_key TEXT NOT NULL UNIQUE,question_pattern TEXT DEFAULT '',answer TEXT NOT NULL,category TEXT DEFAULT 'general',approved INTEGER DEFAULT 1,usage_count INTEGER DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS resume_analyses(id INTEGER PRIMARY KEY AUTOINCREMENT,filename TEXT,job_id INTEGER,overall_score REAL,ats_score REAL,structure_score REAL,content_score REAL,match_score REAL,report TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS analytics_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_key TEXT NOT NULL UNIQUE,job_id INTEGER,event_type TEXT NOT NULL,source TEXT DEFAULT 'app',variant TEXT DEFAULT 'A',experiment_id INTEGER,metadata TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS job_attribution(job_id INTEGER PRIMARY KEY,experiment_id INTEGER,variant TEXT DEFAULT 'A',resume_version_id INTEGER,source TEXT DEFAULT 'organic',first_touch_at TEXT DEFAULT CURRENT_TIMESTAMP,last_touch_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_analytics_job ON analytics_events(job_id,created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type,created_at);
CREATE TABLE IF NOT EXISTS agent_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,agent_name TEXT,task_type TEXT,provider TEXT,model_tier TEXT,status TEXT,input_chars INTEGER DEFAULT 0,output_chars INTEGER DEFAULT 0,estimated_tokens INTEGER DEFAULT 0,cost_units REAL DEFAULT 0,result TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS resume_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER,name TEXT,summary TEXT,skills TEXT,experience TEXT,docx_path TEXT,variant TEXT DEFAULT 'A',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS experiments(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,kind TEXT,status TEXT DEFAULT 'active',control_variant TEXT DEFAULT 'A',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS experiment_events(id INTEGER PRIMARY KEY AUTOINCREMENT,experiment_id INTEGER,job_id INTEGER,variant TEXT,event_type TEXT,event_value REAL DEFAULT 1,metadata TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS followups(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER,due_at TEXT,status TEXT DEFAULT 'pending',channel TEXT DEFAULT 'email',template TEXT,notes TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS email_imports(id INTEGER PRIMARY KEY AUTOINCREMENT,message_id TEXT UNIQUE,sender TEXT,subject TEXT,received_at TEXT,body TEXT,classification TEXT,job_id INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS onboarding(id INTEGER PRIMARY KEY CHECK(id=1),step INTEGER DEFAULT 1,completed INTEGER DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER,kind TEXT,content TEXT,provider TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
'''
@contextmanager
def connect():
 c=sqlite3.connect(DB_PATH);c.row_factory=sqlite3.Row
 try:yield c;c.commit()
 finally:c.close()
def init_db():
 with connect() as c:
  migrate(c,SCHEMA);c.execute("INSERT OR IGNORE INTO settings VALUES('ai_provider','heuristic')")
  from app.services.assistant import seed_answers
  seed_answers(c)
