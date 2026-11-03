"""Offline workspace transfer. Stop CareerOS before invoking this module."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

from app.migrations import SCHEMA_VERSION
from app.version import VERSION

MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def export_workspace(database, uploads, destination):
    database, uploads, destination = map(Path, (database, uploads, destination))
    if not database.is_file():
        raise FileNotFoundError(database)
    if not uploads.is_dir():
        raise FileNotFoundError(uploads)
    if destination.resolve().is_relative_to(uploads.resolve()):
        raise ValueError('Salve o backup fora da pasta de uploads.')
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / 'career_os.db'
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as source:
            with sqlite3.connect(snapshot) as target:
                source.backup(target)
        files = {'career_os.db': snapshot.read_bytes()}
        for path in uploads.rglob('*'):
            if path.is_symlink():
                raise ValueError('Uploads com links simbólicos não são suportados.')
            if path.is_file():
                files['uploads/' + path.relative_to(uploads).as_posix()] = path.read_bytes()
        if sum(map(len, files.values())) > MAX_ARCHIVE_BYTES:
            raise ValueError('Workspace excede o limite de 512 MiB.')
        manifest = {'format': 1, 'app_version': VERSION,
                    'files': {name: digest(data) for name, data in files.items()}}
        # Exclusive creation prevents accidentally overwriting an earlier backup.
        with destination.open('xb') as output:
            try:
                with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr('manifest.json', json.dumps(manifest))
                    for name, data in files.items():
                        archive.writestr(name, data)
            except BaseException:
                output.close()
                destination.unlink(missing_ok=True)
                raise
    return destination


def restore_workspace(archive_path, destination):
    destination = Path(destination).absolute()
    if destination.exists():
        raise FileExistsError('Escolha uma pasta nova para restaurar o workspace.')
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > MAX_ARCHIVE_BYTES:
            raise ValueError('Backup duplicado ou muito grande.')
        for name in names:
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                    or str(path) != name or name.endswith('/')
                    or not (name in {'manifest.json', 'career_os.db'} or name.startswith('uploads/'))):
                raise ValueError('Caminho inválido no backup.')
        if not {'manifest.json', 'career_os.db'}.issubset(names):
            raise ValueError('Backup incompleto.')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format') != 1 or set(manifest.get('files', {})) != set(names) - {'manifest.json'}:
            raise ValueError('Formato de backup inválido.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            stage = Path(temporary) / 'workspace'
            stage.mkdir()
            (stage / 'uploads').mkdir()
            for name, expected_hash in manifest['files'].items():
                data = archive.read(name)
                if digest(data) != expected_hash:
                    raise ValueError('Falha de integridade no backup.')
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with sqlite3.connect(stage / 'career_os.db') as connection:
                if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Banco inválido.')
                if connection.execute('PRAGMA user_version').fetchone()[0] > SCHEMA_VERSION:
                    raise ValueError('Backup exige uma versão mais recente do CareerOS.')
                required = {'profile', 'jobs', 'resume_versions', 'settings'}
                tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not required.issubset(tables):
                    raise ValueError('Backup não contém um banco CareerOS.')
                for row_id, old_path in connection.execute('SELECT id,docx_path FROM resume_versions').fetchall():
                    if not old_path:
                        continue
                    # Older versions persisted absolute Windows paths.
                    filename = old_path.replace('\\', '/').rsplit('/', 1)[-1]
                    if not filename or not (stage / 'uploads' / filename).is_file():
                        raise ValueError('Currículo referenciado está ausente do backup.')
                    connection.execute('UPDATE resume_versions SET docx_path=? WHERE id=?',
                                       (str(destination / 'uploads' / filename), row_id))
            # Reserve the final name exclusively, then move within the same filesystem.
            destination.mkdir()
            try:
                for child in stage.iterdir():
                    shutil.move(str(child), destination / child.name)
            except BaseException:
                shutil.rmtree(destination)
                raise
    return destination


def main():
    parser = argparse.ArgumentParser(description='Backup/restauração offline do CareerOS (feche o app primeiro).')
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('archive', type=Path)
    restore = commands.add_parser('restore')
    restore.add_argument('archive', type=Path)
    restore.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.command == 'export':
        from app.config import DB_PATH, UPLOAD_DIR
        result = export_workspace(DB_PATH, UPLOAD_DIR, args.archive)
    else:
        result = restore_workspace(args.archive, args.destination)
    print(result)


if __name__ == '__main__':
    main()
