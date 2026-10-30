import shutil,subprocess,json
def status(n):
 if n=='heuristic':return {'installed':True,'authenticated':True,'detail':'Local, sem login.'}
 cmd='codex' if n=='codex' else 'claude'
 if not shutil.which(cmd):return {'installed':False,'authenticated':False,'detail':f'{cmd} CLI não instalado.'}
 args=[cmd,'login','status'] if n=='codex' else [cmd,'auth','status'];r=subprocess.run(args,capture_output=True,text=True,timeout=12)
 return {'installed':True,'authenticated':r.returncode==0,'detail':(r.stdout or r.stderr)[:300]}
def login(n):
 cmd=['codex','login'] if n=='codex' else ['claude','auth','login']
 if not shutil.which(cmd[0]):return {'ok':False,'detail':f'Instale {cmd[0]} CLI primeiro.'}
 subprocess.Popen(cmd);return {'ok':True,'detail':'Login iniciado. Conclua no terminal/navegador.'}
def generate(n,p,j,a):
 e=(p.get('evidence') or [{'name':'projeto prático','description':'automação em Python'}])[0];skills=', '.join(a.get('matched_skills') or p.get('skills',[])[:6]);base={'summary':f"Estudante de {p.get('course')} no {p.get('term')}º termo, com prática em {skills}. Desenvolveu {e.get('name')}: {e.get('description')}.",'cover_letter':f"Olá, equipe da {j.get('company')}. Tenho interesse em {j.get('title')}. Meu projeto {e.get('name')} demonstra prática com {skills} e resolução de problemas reais.",'provider':'heuristic'}
 if n=='heuristic' or not status(n)['authenticated']:return base
 prompt=json.dumps({'rule':'Não invente fatos. Responda JSON com summary e cover_letter em pt-BR.','profile':p,'job':j,'analysis':a},ensure_ascii=False);cmd=['codex','exec','--skip-git-repo-check',prompt] if n=='codex' else ['claude','-p',prompt,'--output-format','json']
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=180,check=True);raw=r.stdout;out=json.loads(raw[raw.find('{'):raw.rfind('}')+1]);out['provider']=n;return out
 except:return base
