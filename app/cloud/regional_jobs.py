"""Read only the job cards currently published on the Inova Prudente mural."""
import re
from html.parser import HTMLParser


class InovaCards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self.current = None
        self.text = []
        self.title = ''

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'a' and self.current is None:
            url = attributes.get('href', '')
            if re.fullmatch(r'https://inovaprudente\.com\.br/vagas/\d+/[a-z0-9-]+', url):
                self.current = url
                self.title = attributes.get('title', '')
                self.text = []
        if self.current and tag in ('p', 'br', 'span', 'h2'):
            self.text.append('\n')

    def handle_data(self, data):
        if self.current:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in ('p', 'span', 'h2') and self.current:
            self.text.append('\n')
        if tag != 'a' or self.current is None:
            return
        lines = [' '.join(line.split()) for line in ''.join(self.text).splitlines()]
        lines = [line for line in lines if line and 'quero saber mais' not in line.lower()]
        text = '\n'.join(lines)
        city = re.search(r'Cidade:\s*([^\n]+)', text)
        if self.title and city:
            self.cards.append({
                'title': self.title, 'url': self.current,
                'location': city[1], 'description': text,
                'work_model': 'onsite' if 'Presencial' in lines else
                              'hybrid' if 'Semipresencial' in lines else
                              'remote' if 'Remoto' in lines else '',
                'remote': 'Remoto' in lines,
            })
        self.current = None
        self.text = []
