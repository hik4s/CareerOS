import email,re
from email import policy
from html import unescape
def parse_eml(data):
 msg=email.message_from_bytes(data,policy=policy.default);body=''
 if msg.is_multipart():
  for p in msg.walk():
   if p.get_content_type()=='text/plain':body+=p.get_content()+'\n'
 else:body=msg.get_content()
 text=(msg.get('subject','')+' '+body).lower();classification='interview' if re.search(r'entrevista|interview|conversation',text) else 'rejected' if re.search(r'não seguiremos|nao seguiremos|reprovad|we decided|unfortunately',text) else 'application' if re.search(r'candidatura|application|inscrição',text) else 'other'
 urls=re.findall(r'https?://[^\s<>"\']+',body)
 return {'message_id':msg.get('message-id') or '', 'sender':msg.get('from',''),'subject':msg.get('subject',''),'received_at':str(msg.get('date','')),'body':body[:30000],'classification':classification,'urls':urls[:10]}
