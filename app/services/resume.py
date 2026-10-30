import io,re
from pypdf import PdfReader
SKILLS=['python','playwright','git','github','sql','power bi','excel','fastapi','react','javascript','docker','linux','api','streamlit']
def text_from_pdf(data):return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(data)).pages).strip()
def parse(text):
 def one(p):
  m=re.search(p,text,re.I);return m.group(0) if m else ''
 lines=[x.strip() for x in text.splitlines() if x.strip()];name=next((x for x in lines[:8] if 2<=len(x.split())<=6 and not re.search(r'[@\d:/]',x)),'');low=text.lower();tm=re.search(r'(\d+)[º°o]?\s*(termo|semestre)',low)
 return {'full_name':name,'email':one(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'),'phone':one(r'(?:\(?\d{2}\)?\s*)?\d{4,5}[- ]?\d{4}'),'linkedin':one(r'https?://(?:www\.)?linkedin\.com/[^\s)]+'),'github':one(r'https?://(?:www\.)?github\.com/[^\s)]+'),'term':int(tm.group(1)) if tm else None,'skills':[s for s in SKILLS if s in low]}
