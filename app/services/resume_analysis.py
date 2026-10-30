import io,re
from collections import Counter
from docx import Document
from app.services.scoring import ALIASES
SECTIONS={'resumo':['resumo','objetivo','perfil'],'experiencia':['experiência','experiencia profissional','projetos'],'formacao':['formação','formacao acadêmica','educação'],'habilidades':['habilidades','competências','tecnologias','skills']}
def text_from_docx(data:bytes)->str:
 d=Document(io.BytesIO(data));parts=[p.text for p in d.paragraphs]
 for table in d.tables:
  parts.extend(' | '.join(cell.text for cell in row.cells) for row in table.rows)
 return '\n'.join(parts).strip()
def analyze_resume(text:str,job:dict|None=None)->dict:
 low=text.lower();words=re.findall(r'[a-zá-ú0-9+#.]+',low);wc=len(words);lines=[x.strip() for x in text.splitlines() if x.strip()]
 found={k:any(v in low for v in vals) for k,vals in SECTIONS.items()};contacts={'email':bool(re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}',text,re.I)),'phone':bool(re.search(r'\d{4,5}[- ]?\d{4}',text)),'linkedin':('linkedin.com/' in low),'github':('github.com/' in low)}
 structure=max(0,min(100,25+sum(found.values())*15+(10 if wc>=120 else 0)+(5 if wc<=900 else -10)))
 action=sum(low.count(x) for x in ['desenvolv','automatiz','implementei','criei','otimizei','analisei','reduzi','aumentei']);numbers=len(re.findall(r'\b\d+(?:[.,]\d+)?%?\b',text));content=max(0,min(100,35+action*6+min(numbers,6)*4+(10 if 'projeto' in low else 0)))
 ats=max(0,min(100,25+sum(contacts.values())*8+sum(found.values())*8-(15 if len(lines)<5 else 0)))
 match=50;matched=[];missing=[]
 if job:
  jt=(job.get('title','')+' '+job.get('description','')).lower()
  requested=[k for k,vs in ALIASES.items() if any(v in jt for v in vs)]
  matched=[x for x in requested if x in low];missing=[x for x in requested if x not in low];match=round(100*len(matched)/len(requested),1) if requested else 65
 overall=round(structure*.25+content*.30+ats*.20+match*.25,1)
 strengths=[];improvements=[]
 if found['experiencia']:strengths.append('Apresenta experiência ou projetos.')
 if action>=2:strengths.append('Usa verbos de ação para demonstrar contribuição.')
 if contacts['linkedin'] or contacts['github']:strengths.append('Inclui presença profissional online.')
 if not found['resumo']:improvements.append('Adicionar resumo profissional direcionado ao estágio desejado.')
 if numbers<2:improvements.append('Adicionar resultados mensuráveis seguros, sem expor dados corporativos.')
 if missing:improvements.append('Evidenciar competências reais pedidas pela vaga: '+', '.join(missing)+'.')
 if wc>900:improvements.append('Reduzir o currículo para manter leitura rápida e objetiva.')
 if not contacts['email'] or not contacts['phone']:improvements.append('Completar dados de contato.')
 return {'overall_score':overall,'ats_score':round(ats,1),'structure_score':round(structure,1),'content_score':round(content,1),'match_score':match,'word_count':wc,'sections':found,'contacts':contacts,'matched_keywords':matched,'missing_keywords':missing,'strengths':strengths,'improvements':improvements,'verdict':'forte' if overall>=80 else 'competitivo com ajustes' if overall>=65 else 'precisa de revisão'}
