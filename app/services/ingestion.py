import hashlib,re,ipaddress,socket
from urllib.parse import urlparse
from html import unescape
import feedparser,httpx
def validate(url):
 p=urlparse(url)
 if p.scheme not in {'http','https'} or not p.hostname:raise ValueError('URL HTTP/HTTPS inválida')
 if p.hostname in {'localhost','0.0.0.0'}:raise ValueError('Host local não permitido')
 for x in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80)):
  ip=ipaddress.ip_address(x[4][0])
  if ip.is_private or ip.is_loopback or ip.is_link_local:raise ValueError('Rede privada não permitida')
 return url
def clean(x):return re.sub(r'<[^>]+>',' ',unescape(x or '')).strip()
def norm(x,source):
 title=x.get('title') or 'Vaga sem título';url=x.get('url') or x.get('link') or ''
 return {'title':title,'company':x.get('company') or x.get('author') or source,'url':url,'location':x.get('location',''),'work_model':x.get('work_model',''),'description':clean(x.get('description') or x.get('summary') or title),'salary_min':x.get('salary_min'),'benefits':x.get('benefits',[]),'source':source,'external_id':str(x.get('id') or hashlib.sha256((title+url).encode()).hexdigest())}
def rss(url,name):return [norm(dict(e),name) for e in feedparser.parse(validate(url)).entries]
def pick(obj,path,default=''):
 cur=obj
 for p in path.split('.') if path else []:
  if not isinstance(cur,dict):return default
  cur=cur.get(p,default)
 return cur
def api(url,name,cfg):
 r=httpx.get(validate(url),headers=cfg.get('headers',{}),params=cfg.get('params',{}),timeout=20,follow_redirects=True);r.raise_for_status();payload=r.json();items=pick(payload,cfg.get('items_path',''),payload)
 if not isinstance(items,list):raise ValueError('items_path não aponta para lista')
 return [norm({k:pick(i,v,'') for k,v in cfg.get('mapping',{}).items()},name) for i in items]
