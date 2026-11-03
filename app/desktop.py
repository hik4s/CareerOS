"""Native window and owned loopback server lifecycle."""
import ctypes
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys
import tempfile
import threading
import time
from urllib.request import urlopen

HOST, PORT = '127.0.0.1', 8765
URL = f'http://{HOST}:{PORT}'


def native_error(message):
    if sys.platform == 'win32':
        ctypes.windll.user32.MessageBoxW(None, str(message), 'CareerOS', 0x10)
    else:
        print(f'CareerOS: {message}', file=sys.stderr)


class InstanceLock:
    def __init__(self):
        self.handle = None

    def acquire(self):
        if sys.platform != 'win32':
            return True  # The exclusive listening socket also protects other platforms.
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel.CreateMutexW.restype = wintypes.HANDLE
        self.handle = kernel.CreateMutexW(None, False, 'Local\\CareerOS.Desktop')
        if not self.handle:
            raise OSError(ctypes.get_last_error(), 'Cannot create CareerOS instance mutex')
        return ctypes.get_last_error() != 183

    def close(self):
        if self.handle:
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel.CloseHandle(self.handle)
            self.handle = None


def prepare_data():
    """Copy legacy source data once, retaining the original for recovery."""
    target = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'CareerOS'
    legacy = Path(sys.executable).parent / 'data' if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'data'
    marker = target / '.legacy-migrated'
    if (legacy / 'career_os.db').exists() and not marker.exists():
        if (target / 'career_os.db').exists():
            raise RuntimeError(f'Both legacy and current databases exist. Keep a backup and merge or move the legacy folder before starting. Legacy: {legacy}; current: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='CareerOS-migration-', dir=target.parent))
        try:
            shutil.copytree(legacy, staging, dirs_exist_ok=True)
            # SQLite backup includes committed WAL content instead of copying a stale DB.
            with sqlite3.connect(legacy / 'career_os.db') as source, sqlite3.connect(staging / 'career_os.db') as dest:
                source.backup(dest)
            for suffix in ('-wal', '-shm'):
                (staging / ('career_os.db' + suffix)).unlink(missing_ok=True)
            (staging / '.legacy-migrated').write_text(str(legacy), encoding='utf-8')
            if target.exists():
                if any(target.iterdir()):
                    raise RuntimeError(f'Data migration requires review: destination is not empty: {target}. Legacy data remains at {legacy}.')
                target.rmdir()
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    target.mkdir(parents=True, exist_ok=True)
    return target


class DesktopRuntime:
    def __init__(self, app, webview):
        self.app, self.webview = app, webview
        self.window = None
        self.server = self.thread = self.sock = None
        self.operation_lock = threading.RLock()
        self.closing = False

    def start_server(self, timeout=20):
        import uvicorn
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if sys.platform == 'win32':
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, PORT))
            sock.listen(128)
            self.sock = sock
            self.server = uvicorn.Server(uvicorn.Config(self.app, host=HOST, port=PORT, log_level='warning', timeout_graceful_shutdown=10))
            self.thread = threading.Thread(target=self.server.run, kwargs={'sockets': [sock]}, daemon=True, name='CareerOS-server')
            self.thread.start()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if not self.thread.is_alive():
                    raise RuntimeError('The local server stopped during startup. Check application logs and database permissions.')
                if self.server.started:
                    try:
                        with urlopen(URL + '/api/health', timeout=.5) as response:
                            if response.status == 200 and json.load(response).get('status') == 'ok':
                                return
                    except (OSError, ValueError):
                        pass
                time.sleep(.05)
            raise RuntimeError('CareerOS local server did not become ready within 20 seconds.')
        except BaseException:
            self.stop_server()
            sock.close()
            raise

    def stop_server(self):
        if self.server:
            self.server.should_exit = True
        if self.thread and self.thread.is_alive():
            self.thread.join(15)
            if self.thread.is_alive():
                raise RuntimeError('The server is still processing requests. Maintenance was cancelled to protect your data.')
        if self.sock:
            self.sock.close()
        self.server = self.thread = self.sock = None

    def shutdown(self, *_):
        with self.operation_lock:
            self.closing = True
            self.stop_server()

    def run_exclusive(self, operation, close=False):
        """Run maintenance with no active backend requests; preserve callback result."""
        with self.operation_lock:
            if self.closing:
                raise RuntimeError('CareerOS is closing.')
            self.stop_server()
            try:
                result = operation()
            except BaseException:
                self.start_server()
                raise
            if close:
                self.closing = True
            else:
                self.start_server()
        # Do not hold a worker lock while dispatching an action to the GUI thread.
        if close and self.window:
            self.window.destroy()
        return result

    def run(self):
        from app.desktop_actions import DesktopActions
        try:
            self.start_server()
            self.window = self.webview.create_window('CareerOS', URL, js_api=DesktopActions(self), width=1280, height=860, min_size=(900, 600))
            self.window.events.closed += self.shutdown
            options = {'gui': 'edgechromium'} if sys.platform == 'win32' else {}
            self.webview.start(**options)
        finally:
            self.shutdown()


def main():
    lock = InstanceLock()
    try:
        if not lock.acquire():
            native_error('CareerOS is already running. Use the existing CareerOS window.')
            return 1
        os.environ['CAREER_OS_DESKTOP'] = '1'
        data_root = prepare_data()
        logging.basicConfig(filename=data_root / 'desktop.log', level=logging.INFO, encoding='utf-8')
        import webview
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
        from app.main import app
        DesktopRuntime(app, webview).run()
        return 0
    except Exception as exc:
        logging.exception('Desktop runtime failed')
        native_error(f'CareerOS could not start: {exc}\n\nClose other applications using port 8765 and retry. On Windows install Microsoft Edge WebView2 Runtime, and check that your CareerOS data folder is writable.')
        return 1
    finally:
        lock.close()
