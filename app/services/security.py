import json,hashlib
SERVICE='CareerOS'
def set_secret(name,value):
 import keyring;keyring.set_password(SERVICE,name,value)
def get_secret(name):
 try:
  import keyring;return keyring.get_password(SERVICE,name)
 except:return None
def redact(text):
 import re
 text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[EMAIL]',text)
 text=re.sub(r'(?i)(bearer|token|api[_ -]?key|password)\s*[:=]\s*\S+',r'\1=[REDACTED]',text)
 return text
def fingerprint(text):return hashlib.sha256(text.encode()).hexdigest()[:16]
