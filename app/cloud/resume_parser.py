"""Bounded subprocess parser for untrusted uploaded documents."""
from io import BytesIO
import json
import sys


def extract(content, extension):
    if extension == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > 30:
            raise ValueError('Limite de 30 páginas por currículo.')
        parts = []
        size = 0
        for page in reader.pages:
            part = page.extract_text() or ''
            size += len(part)
            if size > 200000:
                raise ValueError('Texto do currículo excede o limite.')
            parts.append(part)
        return '\n'.join(parts)
    if extension == '.docx':
        from docx import Document
        doc = Document(BytesIO(content))
        text = '\n'.join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
        if len(text) > 200000:
            raise ValueError('Texto do currículo excede o limite.')
        return text
    raise ValueError('Formato inválido.')


def main():
    if sys.platform == 'linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (192 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    try:
        data = sys.stdin.buffer.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError('Arquivo muito grande.')
        result = extract(data, sys.argv[1])
        # Pipes use the Windows code page by default; the parent expects UTF-8 JSON.
        sys.stdout.buffer.write(json.dumps({'text': result}, ensure_ascii=False).encode('utf-8'))
    except Exception:
        # Never echo file contents or parser internals into the API/log output.
        print(json.dumps({'error': 'Não foi possível extrair o texto dentro dos limites de processamento.'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
