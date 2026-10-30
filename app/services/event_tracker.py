import json,uuid
from app.services.learning import EVENT_WEIGHTS
STAGE_EVENTS={'applied':'applied','interview':'interview','offer':'offer','rejected':'rejected'}

def ensure_default_experiment(con):
 row=con.execute("SELECT id FROM experiments WHERE status='active' ORDER BY id LIMIT 1").fetchone()
 if row:return row['id']
 cur=con.execute("INSERT INTO experiments(name,kind,status,control_variant) VALUES('Curriculo por vaga','resume','active','A')")
 return cur.lastrowid

def attribution(con,job_id):
 row=con.execute('SELECT * FROM job_attribution WHERE job_id=?',(job_id,)).fetchone()
 if row:return dict(row)
 eid=ensure_default_experiment(con)
 con.execute('INSERT OR IGNORE INTO job_attribution(job_id,experiment_id,variant,source) VALUES(?,?,?,?)',(job_id,eid,'A','organic'))
 return {'job_id':job_id,'experiment_id':eid,'variant':'A','resume_version_id':None,'source':'organic'}

def set_attribution(con,job_id,variant='A',resume_version_id=None,source=None):
 current=attribution(con,job_id)
 con.execute('''INSERT INTO job_attribution(job_id,experiment_id,variant,resume_version_id,source,last_touch_at)
 VALUES(?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(job_id) DO UPDATE SET variant=excluded.variant,resume_version_id=COALESCE(excluded.resume_version_id,job_attribution.resume_version_id),source=COALESCE(excluded.source,job_attribution.source),last_touch_at=CURRENT_TIMESTAMP''',(job_id,current['experiment_id'],variant,resume_version_id,source or current['source']))

def track(con,job_id,event_type,source='app',metadata=None,event_key=None):
 attr=attribution(con,job_id);key=event_key or f"{job_id}:{event_type}:{uuid.uuid4().hex}"
 try:
  con.execute('INSERT INTO analytics_events(event_key,job_id,event_type,source,variant,experiment_id,metadata) VALUES(?,?,?,?,?,?,?)',(key,job_id,event_type,source,attr['variant'],attr['experiment_id'],json.dumps(metadata or {},ensure_ascii=False)))
  con.execute('INSERT INTO experiment_events(experiment_id,job_id,variant,event_type,event_value,metadata) VALUES(?,?,?,?,?,?)',(attr['experiment_id'],job_id,attr['variant'],event_type,EVENT_WEIGHTS.get(event_type,1),json.dumps(metadata or {},ensure_ascii=False)))
  return True
 except Exception:return False

def track_stage(con,job_id,stage,previous=None):
 event=STAGE_EVENTS.get(stage)
 if not event:return False
 return track(con,job_id,event,'pipeline',{'previous_stage':previous,'new_stage':stage},f'{job_id}:stage:{stage}')

def learning_snapshot(con):
 totals={r['event_type']:r['n'] for r in con.execute('SELECT event_type,COUNT(*) n FROM analytics_events GROUP BY event_type')}
 variants=[dict(r) for r in con.execute('''SELECT variant,COUNT(DISTINCT CASE WHEN event_type='applied' THEN job_id END) applied,COUNT(DISTINCT CASE WHEN event_type='interview' THEN job_id END) interviews,COUNT(DISTINCT CASE WHEN event_type='offer' THEN job_id END) offers,COUNT(*) events FROM analytics_events GROUP BY variant ORDER BY variant''')]
 for r in variants:
  r['interview_rate']=round(100*r['interviews']/r['applied'],1) if r['applied'] else 0
  r['offer_rate']=round(100*r['offers']/r['applied'],1) if r['applied'] else 0
 return {'totals':totals,'variants':variants,'event_count':sum(totals.values())}
