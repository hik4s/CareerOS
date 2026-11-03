import socket
import sqlite3

import pytest
from app.desktop import DesktopRuntime, HOST, PORT, prepare_data


def test_port_conflict_does_not_start_backend():
    blocker = socket.socket()
    blocker.bind((HOST, PORT))
    blocker.listen()
    runtime = DesktopRuntime(None, None)
    try:
        with pytest.raises(OSError):
            runtime.start_server()
        assert runtime.thread is None
    finally:
        blocker.close()


def test_exclusive_stops_before_callback_and_restarts():
    runtime = DesktopRuntime(None, None)
    events = []
    runtime.stop_server = lambda: events.append('stop')
    runtime.start_server = lambda: events.append('start')
    assert runtime.run_exclusive(lambda: events.append('operation') or 42) == 42
    assert events == ['stop', 'operation', 'start']


def test_exclusive_restarts_on_failure():
    runtime = DesktopRuntime(None, None)
    events = []
    runtime.stop_server = lambda: events.append('stop')
    runtime.start_server = lambda: events.append('start')
    def fail():
        raise ValueError('bad archive')
    with pytest.raises(ValueError, match='bad archive'):
        runtime.run_exclusive(fail, close=True)
    assert events == ['stop', 'start']
    assert not runtime.closing


def test_close_after_success_keeps_server_stopped():
    runtime = DesktopRuntime(None, None)
    events = []
    runtime.stop_server = lambda: events.append('stop')
    runtime.start_server = lambda: events.append('start')
    class Window:
        def destroy(self):
            events.append('destroy')
    runtime.window = Window()
    runtime.run_exclusive(lambda: events.append('update'), close=True)
    assert events == ['stop', 'update', 'destroy']
    assert runtime.closing


def test_real_server_readiness_and_shutdown():
    from fastapi import FastAPI
    app = FastAPI()
    @app.get('/api/health')
    def health():
        return {'status': 'ok'}
    runtime = DesktopRuntime(app, None)
    try:
        runtime.start_server(timeout=5)
        thread = runtime.thread
        assert thread.is_alive()
    finally:
        runtime.shutdown()
    assert not thread.is_alive()
    assert runtime.sock is None


def test_legacy_migration_preserves_database_and_source(tmp_path, monkeypatch):
    import app.desktop as desktop
    root = tmp_path / 'source'
    (root / 'app').mkdir(parents=True)
    legacy = root / 'data'
    legacy.mkdir()
    with sqlite3.connect(legacy / 'career_os.db') as db:
        db.execute('create table example(value text)')
        db.execute("insert into example values ('kept')")
    monkeypatch.setattr(desktop, '__file__', str(root / 'app' / 'desktop.py'))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    target = prepare_data()
    with sqlite3.connect(target / 'career_os.db') as db:
        assert db.execute('select value from example').fetchone() == ('kept',)
    assert (legacy / 'career_os.db').exists()
    assert prepare_data() == target


def test_legacy_conflict_is_explicit(tmp_path, monkeypatch):
    import app.desktop as desktop
    root = tmp_path / 'source'
    (root / 'app').mkdir(parents=True)
    (root / 'data').mkdir()
    (root / 'data' / 'career_os.db').touch()
    target = tmp_path / 'local' / 'CareerOS'
    target.mkdir(parents=True)
    (target / 'career_os.db').touch()
    monkeypatch.setattr(desktop, '__file__', str(root / 'app' / 'desktop.py'))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    with pytest.raises(RuntimeError, match='Both legacy and current databases'):
        prepare_data()


def test_readiness_failure_cleans_server():
    from fastapi import FastAPI
    runtime = DesktopRuntime(FastAPI(), None)
    with pytest.raises(RuntimeError, match='did not become ready'):
        runtime.start_server(timeout=.2)
    assert runtime.thread is None
    assert runtime.sock is None
