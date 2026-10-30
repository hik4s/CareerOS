import json,math
EVENT_WEIGHTS={'view':.1,'captured':.2,'applied':1,'response':2,'interview':5,'offer':10,'rejected':0}
def record(con,experiment_id,job_id,variant,event,metadata=None):con.execute('INSERT INTO experiment_events(experiment_id,job_id,variant,event_type,event_value,metadata) VALUES(?,?,?,?,?,?)',(experiment_id,job_id,variant,event,EVENT_WEIGHTS.get(event,1),json.dumps(metadata or {})))
def report(con):
 rows=[dict(r) for r in con.execute('''SELECT e.name,x.variant,COUNT(*) events,SUM(x.event_type='applied') applied,SUM(x.event_type='interview') interviews,SUM(x.event_type='offer') offers,SUM(x.event_value) weighted FROM experiment_events x JOIN experiments e ON e.id=x.experiment_id GROUP BY e.name,x.variant''')]
 for r in rows:r['interview_rate']=round(100*r['interviews']/r['applied'],1) if r['applied'] else 0
 return rows
