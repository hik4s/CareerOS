from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import pytest
from docx import Document
from pypdf import PdfWriter
from app.cloud.resume_parser import extract


def test_docx_extraction_in_resource_limited_process():
    document = Document()
    document.add_paragraph('Experiência real: Python e SQL')
    stream = BytesIO()
    document.save(stream)
    result = subprocess.run([sys.executable, '-m', 'app.cloud.resume_parser', '.docx'], input=stream.getvalue(), capture_output=True, timeout=20)
    assert result.returncode == 0
    assert json.loads(result.stdout)['text'] == 'Experiência real: Python e SQL'


def test_page_limit_rejects_oversized_pdf():
    writer = PdfWriter()
    for _ in range(31):
        writer.add_blank_page(width=100, height=100)
    stream = BytesIO()
    writer.write(stream)
    with pytest.raises(ValueError, match='30 páginas'):
        extract(stream.getvalue(), '.pdf')


def test_malformed_file_does_not_echo_input():
    result = subprocess.run([sys.executable, '-m', 'app.cloud.resume_parser', '.docx'], input=b'private-contents', capture_output=True, timeout=20)
    assert result.returncode == 1
    assert b'private-contents' not in result.stdout + result.stderr
