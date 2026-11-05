"""Explainable career-fit rules. Personal profile data stays on this server."""
import re
import unicodedata


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


TECH = re.compile(r'\b(?:ti|t\.i\.?|informatica|software|python|programa(?:dor|dora|cao)|'
                  r'desenvolvedor\w*|desenvolvimento|computer science|ciencia da computacao|sistemas de informacao|developer|front.?end|back.?end|full.?stack|'
                  r'data science|ciencia de dados|inteligencia artificial|machine learning|'
                  r'automacao|power platform|power apps|power automate|copilot studio|ai builder|'
                  r'analista de sistemas|suporte (?:de |em |a )?ti|redes de computadores)\b')
ENTRY = re.compile(r'\b(?:estagio|estagiari\w*|aprendiz|trainee|junior|jr|internship|intern)\b')
SENIOR = re.compile(r'\b(?:senior|sr|pleno|plena|staff|principal|lead|gerente|coordenador\w*|diretor\w*)\b')
UNRELATED_TITLE = re.compile(r'\b(?:contabil|contabeis|contabilidade|direito|juridic\w*|'
                             r'enfermagem|medicina|engenharia civil|arquitetura|'
                             r'administrativ\w*|comercial|vendas|marketing|cozinha|limpeza)\b')
GENERIC_SKILLS = {'comunicacao', 'trabalho em equipe', 'proatividade', 'organizacao', 'ingles', 'portugues'}


def career_fit(job, profile, query):
    roles = profile.get('target_roles') or []
    skills = profile.get('skills') or []
    facts = ' '.join(str(item) for item in [*roles, *skills, profile.get('course', '')])
    technical = bool(TECH.search(fold(facts or query)))
    title = fold(job['title'])
    body = fold(job.get('description', ''))
    if technical and UNRELATED_TITLE.search(title) and not TECH.search(title):
        return False, []
    if technical and not TECH.search(title + ' ' + body):
        return False, []
    entry = bool(ENTRY.search(fold(' '.join(str(item) for item in roles))))
    if entry and SENIOR.search(title):
        return False, []
    # Explicit role/skill evidence is required for profiles outside the technical domain.
    terms = [fold(str(item).strip()) for item in [*roles, *skills]
             if len(str(item).strip()) >= 3 and fold(str(item).strip()) not in GENERIC_SKILLS]
    matches = [term for term in terms if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', title + ' ' + body)]
    if not technical and terms and not matches:
        return False, []
    reasons = ['Área de tecnologia identificada'] if technical else []
    if entry and ENTRY.search(title):
        reasons.append('Nível inicial identificado')
    reasons.extend('Perfil: ' + term for term in matches[:3])
    return True, reasons
