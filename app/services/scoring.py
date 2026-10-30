import re
ALIASES={'python':['python'],'playwright':['playwright','automação web'],'sql':['sql','banco de dados'],'git':['git','github'],'api':['api','rest','fastapi'],'power bi':['power bi','dashboard',' bi '],'qa':['qa','testes'],'docker':['docker'],'linux':['linux'],'javascript':['javascript'],'react':['react']}
def analyze(p,j):
 text=(j.get('title','')+' '+j.get('description','')).lower();skills=[x.lower() for x in p.get('skills',[])];matched=[];missing=[]
 for k,vals in ALIASES.items():
  if any(v in text for v in vals):(matched if k in skills or any(v in skills for v in vals) else missing).append(k)
 m=re.search(r'(?:a partir do|mínimo|cursando).*?(\d+)[º°o]?\s*(?:termo|semestre)',text);req=int(m.group(1)) if m else None;blockers=[]
 if req and p.get('term',1)<req:blockers.append(f'Exige a partir do {req}º termo; perfil informa {p.get("term")}º termo.')
 score=max(0,min(100,25+len(matched)*10+min(15,len(p.get('evidence',[]))*5)-len(missing)*3-len(blockers)*40))
 return {'score':score,'matched_skills':matched,'missing_skills':missing,'blockers':blockers,'required_term':req,'recommendation':'apply' if score>=65 and not blockers else 'review' if score>=40 else 'skip'}
