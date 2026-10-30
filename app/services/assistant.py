import re
DEFAULTS=[
 ('tell_about_you',r'conte sobre voc|fale sobre voc|apresente-se','Sou estudante de Bacharelado em Tecnologia da Informação e desenvolvo projetos práticos de automação com Python. Tenho experiência prática com investigação de falhas, automação web, organização de dados, logs e melhoria contínua. Busco um estágio para contribuir em problemas reais e evoluir com acompanhamento técnico.','presentation'),
 ('availability',r'disponibilidade|horário|horario','Tenho disponibilidade compatível com a jornada de estágio informada e posso alinhar os horários às atividades acadêmicas.','logistics'),
 ('why_company',r'por que.*empresa|por que.*vaga|motivação|motivacao','Tenho interesse pela oportunidade de aplicar desenvolvimento e automação em desafios reais, aprender com uma equipe experiente e contribuir com autonomia, curiosidade técnica e melhoria de processos.','motivation'),
 ('salary',r'pretensão|pretensao|bolsa','Busco uma bolsa compatível com o escopo da vaga e com o mercado, considerando também o pacote de benefícios e as oportunidades de desenvolvimento.','logistics'),
 ('experience',r'experi.ncia|projeto|tecnologias','Meu principal projeto público é uma solução sanitizada de automação em Python, com navegação web, processamento de arquivos, logs, acompanhamento de execução e dashboard.','technical')]
def seed_answers(con):
 for k,p,a,c in DEFAULTS:con.execute('INSERT OR IGNORE INTO answer_bank(question_key,question_pattern,answer,category) VALUES(?,?,?,?)',(k,p,a,c))
def suggestions(con,questions:list[str]):
 rows=[dict(r) for r in con.execute('SELECT * FROM answer_bank WHERE approved=1')];out=[]
 for q in questions:
  hit=next((r for r in rows if re.search(r['question_pattern'],q,re.I)),None);out.append({'question':q,'answer':hit['answer'] if hit else '','answer_id':hit['id'] if hit else None,'requires_review':True})
 return out
