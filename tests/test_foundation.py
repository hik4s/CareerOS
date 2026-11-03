import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_version_consistent():
    from app.main import app, health
    from app.version import VERSION
    assert app.version == health()['version'] == VERSION


def test_migrate_legacy_preserves_data(tmp_path, monkeypatch):
    import app.db as db
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'legacy.db')
    with sqlite3.connect(db.DB_PATH) as c:
        c.execute('CREATE TABLE resume_versions(id INTEGER PRIMARY KEY,job_id INTEGER,name TEXT,summary TEXT,skills TEXT,experience TEXT,docx_path TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        c.execute("INSERT INTO resume_versions(id,name) VALUES(7,'original')")
    db.init_db()
    db.init_db()
    with db.connect() as c:
        row = c.execute('SELECT * FROM resume_versions WHERE id=7').fetchone()
        assert row['name'] == 'original'
        assert row['variant'] == 'A'
        assert c.execute('PRAGMA user_version').fetchone()[0] == 1


def test_newer_database_untouched(tmp_path, monkeypatch):
    import app.db as db
    import pytest
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'future.db')
    with sqlite3.connect(db.DB_PATH) as c:
        c.execute('PRAGMA user_version=99')
    with pytest.raises(RuntimeError, match='mais recente'):
        db.init_db()
    with sqlite3.connect(db.DB_PATH) as c:
        assert c.execute('PRAGMA user_version').fetchone()[0] == 99
        assert not c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()


def test_api_health_and_profile(tmp_path, monkeypatch):
    import app.db as db
    from app.main import app
    from app.version import VERSION
    from fastapi.testclient import TestClient
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'api.db')
    with TestClient(app) as client:
        assert client.get('/api/health').json()['version'] == VERSION
        assert client.get('/openapi.json').json()['info']['version'] == VERSION
        assert client.put('/api/profile', json={'full_name': 'Exemplo', 'skills': ['python']}).status_code == 200
        assert client.get('/api/profile').json()['full_name'] == 'Exemplo'


def test_migration_failure_rolls_back(tmp_path, monkeypatch):
    import app.db as db
    import pytest
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'unsupported.db')
    with sqlite3.connect(db.DB_PATH) as c:
        c.execute('CREATE TABLE profile(id INTEGER PRIMARY KEY,data TEXT NOT NULL)')
        c.execute("INSERT INTO profile VALUES(1,'original')")
    with pytest.raises(RuntimeError, match='preservado'):
        db.init_db()
    with sqlite3.connect(db.DB_PATH) as c:
        assert [r[1] for r in c.execute('PRAGMA table_info(profile)')] == ['id', 'data']
        assert c.execute('SELECT data FROM profile').fetchone()[0] == 'original'
        assert c.execute('PRAGMA user_version').fetchone()[0] == 0
