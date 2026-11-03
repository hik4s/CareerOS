import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_workspace_roundtrip(tmp_path, monkeypatch):
    import app.db as db
    from app.workspace import export_workspace, restore_workspace
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'source.db')
    db.init_db()
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    (uploads / 'cv.docx').write_bytes(b'example resume')
    with db.connect() as c:
        c.execute("INSERT INTO jobs(title,company,description) VALUES('Estágio','ACME','Python')")
        c.execute('INSERT INTO resume_versions(docx_path) VALUES(?)', (str(uploads / 'cv.docx'),))
    archive = tmp_path / 'backup.zip'
    export_workspace(db.DB_PATH, uploads, archive)
    target = tmp_path / 'restored'
    restore_workspace(archive, target)
    assert (target / 'uploads/cv.docx').read_bytes() == b'example resume'
    with sqlite3.connect(target / 'career_os.db') as c:
        assert c.execute('SELECT title FROM jobs').fetchone()[0] == 'Estágio'
        assert c.execute('SELECT docx_path FROM resume_versions').fetchone()[0] == str(target / 'uploads/cv.docx')
    with pytest.raises(FileExistsError):
        restore_workspace(archive, target)


def test_reject_tampered_archive(tmp_path, monkeypatch):
    import app.db as db
    from app.workspace import export_workspace, restore_workspace
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'source.db')
    db.init_db()
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    archive = tmp_path / 'backup.zip'
    export_workspace(db.DB_PATH, uploads, archive)
    with zipfile.ZipFile(archive) as z:
        entries = {name: z.read(name) for name in z.namelist()}
    entries['career_os.db'] = b'corrupted'
    with zipfile.ZipFile(archive, 'w') as z:
        for name, content in entries.items():
            z.writestr(name, content)
    target = tmp_path / 'restored'
    with pytest.raises(ValueError, match='integridade'):
        restore_workspace(archive, target)
    assert not target.exists()


def test_reject_path_traversal(tmp_path):
    from app.workspace import restore_workspace
    archive = tmp_path / 'evil.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('../outside', 'bad')
    with pytest.raises(ValueError):
        restore_workspace(archive, tmp_path / 'target')
    assert not (tmp_path / 'outside').exists()
