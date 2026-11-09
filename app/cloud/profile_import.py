"""Conservative, local suggestions from resume text; never persists a profile."""
import re
import unicodedata
from .proximity import city_index


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


HEADINGS = {
    'curriculo', 'curriculum vitae', 'dados pessoais', 'contato', 'contatos',
    'resumo', 'resumo profissional', 'perfil profissional', 'objetivo', 'objetivo profissional',
    'formacao', 'formacao academica', 'educacao', 'experiencia', 'experiencia profissional',
    'experiencias profissionais', 'projetos', 'projetos pessoais', 'habilidades',
    'competencias', 'competencias tecnicas', 'tecnologias', 'skills', 'cursos', 'idiomas',
    'certificacoes', 'informacoes adicionais',
}
SKILLS = ('Python', 'JavaScript', 'TypeScript', 'Java', 'Kotlin', 'C++', 'C#', 'SQL',
          'PostgreSQL', 'MySQL', 'SQLite', 'React', 'Next.js', 'Node.js', 'HTML', 'CSS',
          'FastAPI', 'Django', 'Flask', 'Playwright', 'Selenium', 'Git', 'GitHub', 'Docker',
          'Linux', 'Power BI', 'Excel', 'Streamlit', 'Pandas', 'NumPy', 'Supabase', 'AWS',
          'Terraform', 'Figma', 'Scrum', 'Comunicação', 'Trabalho em equipe', 'Inglês')


def profile_suggestions(text):
    lines = [line.strip(' \t•·')[:1000] for line in text[:200000].splitlines() if line.strip()]
    result = {}

    def put(key, value, limit=500):
        value = value.strip()
        if value:
            result[key] = value[:limit]

    def labeled(labels):
        for line in lines:
            if ':' in line and folded(line.split(':', 1)[0].strip()) in labels:
                return line.split(':', 1)[1].strip()
        return ''

    def section(labels):
        values, active = [], False
        for line in lines:
            head, separator, tail = line.partition(':')
            normalized = folded(head.strip())
            if normalized in HEADINGS:
                if active:
                    break
                active = normalized in labels
                if active and separator and tail.strip():
                    values.append(tail.strip())
            elif active:
                values.append(line)
        return values

    name = labeled({'nome', 'nome completo'})
    if not name:
        for line in lines[:5]:
            if (folded(line) not in HEADINGS and 2 <= len(line.split()) <= 6
                    and re.fullmatch(r"[^\W\d_]+(?:[ '\-][^\W\d_]+)+", line, re.UNICODE)
                    and folded(line) not in city_index()
                    and not re.search(r'estagio|desenvolv|analista|engenheir|bacharel|tecnolog|curricul|profission|ciencia|computacao|ensino|formacao|software|engineer|developer|assistant|administrativ', folded(line))):
                name = line
                break
    put('full_name', name)
    email = re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text)
    if email:
        put('email', email.group())
    phone = re.search(r'(?<!\d)(?:\+55\s*)?\(?[1-9]\d\)?\s*9?\d{4}[- .]?\d{4}(?!\d)', text)
    if phone:
        put('phone', phone.group())
    for key, host in [('linkedin', 'linkedin.com/in/'), ('github', 'github.com/')]:
        link = re.search(r'(?:https?://)?(?:www\.)?' + re.escape(host) + r'[A-Za-z0-9_-]+/?', text, re.I)
        if link:
            put(key, re.sub(r'^http://', 'https://', link.group()) if link.group().startswith(('https://', 'http://')) else 'https://' + link.group())
    put('city', labeled({'cidade', 'localidade', 'localizacao'}))
    education = section({'formacao', 'formacao academica', 'educacao'})
    course = labeled({'curso', 'formacao', 'formacao academica'})
    if not course:
        course = next((line for line in education if re.search(r'bacharel|licenciatura|tecnolog|tecnic|graduacao|ensino|mestrado|doutorado|mba', folded(line))), '')
    put('course', course)
    term = re.search(r'\b(\d{1,2})\s*[º°o]?\s*(?:semestre|termo)\b', folded(text))
    if term and 1 <= int(term.group(1)) <= 20:
        result['term'] = int(term.group(1))
    put('graduation_date', labeled({'previsao de conclusao', 'conclusao prevista', 'conclusao'}))
    summary = section({'resumo', 'resumo profissional', 'perfil profissional'})
    put('summary', '\n'.join(summary), 10000)
    roles = section({'objetivo', 'objetivo profissional'})
    if roles:
        result['target_roles'] = [line[:500] for line in roles[:10]]
    skill_lines = section({'habilidades', 'competencias', 'competencias tecnicas', 'tecnologias', 'skills'})
    # Keep explicitly listed skills, including those outside the technical vocabulary.
    skills = []
    if skill_lines:
        for value in re.split(r'[,;|\n•]', '\n'.join(skill_lines)):
            value = value.strip()
            if value and len(value) <= 100 and folded(value) not in {folded(s) for s in skills}:
                skills.append(value)
    else:
        for skill in SKILLS:
            if re.search(r'(?<!\w)' + re.escape(folded(skill)) + r'(?!\w)', folded(text)):
                skills.append(skill)
    if skills:
        result['skills'] = skills[:100]
    return result
