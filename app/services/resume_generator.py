import io,re
from docx import Document
from docx.shared import Pt,Inches,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def generate_docx(profile,job,analysis):
 d=Document();sec=d.sections[0];sec.top_margin=Inches(.55);sec.bottom_margin=Inches(.55);sec.left_margin=Inches(.65);sec.right_margin=Inches(.65)
 normal=d.styles['Normal'];normal.font.name='Arial';normal.font.size=Pt(10)
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(profile.get('full_name',''));r.bold=True;r.font.size=Pt(17);r.font.color.rgb=RGBColor(25,40,75)
 contact=' | '.join(x for x in [profile.get('city'),profile.get('phone'),profile.get('email'),profile.get('linkedin'),profile.get('github')] if x);p=d.add_paragraph(contact);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
 d.add_heading('OBJETIVO',1);d.add_paragraph(f"Estágio em {job.get('title','Tecnologia')} na {job.get('company','empresa-alvo')}")
 matched=analysis.get('matched_skills',[]);evidence=profile.get('evidence',[])
 d.add_heading('RESUMO PROFISSIONAL',1);d.add_paragraph(f"Estudante de {profile.get('course','Tecnologia da Informação')}, no {profile.get('term','')}º termo, com experiência prática em {', '.join(matched or profile.get('skills',[])[:7])}. Interesse em desenvolvimento, automação e melhoria de processos.")
 d.add_heading('PROJETOS E EXPERIÊNCIA PRÁTICA',1)
 for e in evidence:
  p=d.add_paragraph(style='List Bullet');p.add_run(e.get('name','Projeto')).bold=True;p.add_run(' — '+e.get('description',''))
 d.add_heading('COMPETÊNCIAS',1);d.add_paragraph(' • '.join(matched+ [x for x in profile.get('skills',[]) if x not in matched][:8]))
 d.add_heading('FORMAÇÃO',1);d.add_paragraph(f"{profile.get('course','')} — {profile.get('term','')}º termo. Previsão: {profile.get('graduation_date') or 'informar'}")
 buf=io.BytesIO();d.save(buf);return buf.getvalue()
