"""Stable public GitHub Releases only; never executes downloaded code itself."""
from dataclasses import dataclass, asdict
import hashlib
from pathlib import Path
import re
import threading

import httpx
from app.version import VERSION

REPOSITORY = 'hik4s/CareerOS'
API = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
MAX_INSTALLER_BYTES = 512 * 1024 * 1024


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise ValueError('Versão estável inválida.')
    return tuple(map(int, value.removeprefix('v').split('.')))


@dataclass(frozen=True)
class Release:
    version: str
    name: str
    url: str
    checksum_url: str
    size: int
    notes: str


def parse_release(data):
    if data.get('draft') or data.get('prerelease'):
        raise ValueError('Release ainda não é estável.')
    tag = data.get('tag_name', '')
    version_tuple(tag)
    version = tag.removeprefix('v')
    name = f'CareerOS-Setup-{version}.exe'
    assets = data.get('assets', [])
    matches = [a for a in assets if a.get('name') == name]
    hashes = [a for a in assets if a.get('name') == name + '.sha256']
    if len(matches) != 1 or len(hashes) != 1:
        raise ValueError('Release sem instalador e checksum únicos.')
    installer, checksum = matches[0], hashes[0]
    prefix = f'https://github.com/{REPOSITORY}/releases/download/{tag}/'
    if installer.get('browser_download_url') != prefix + name or checksum.get('browser_download_url') != prefix + name + '.sha256':
        raise ValueError('Origem do instalador inválida.')
    size = installer.get('size')
    if not isinstance(size, int) or not 0 < size <= MAX_INSTALLER_BYTES:
        raise ValueError('Tamanho de instalador inválido.')
    return Release(version, name, prefix + name, prefix + name + '.sha256', size, str(data.get('body') or '')[:12000])


class UpdateService:
    def __init__(self, directory, client=None, current=VERSION):
        self.directory = Path(directory)
        self.client = client or httpx.Client(timeout=httpx.Timeout(30, connect=8), follow_redirects=True,
                                             headers={'User-Agent': f'CareerOS/{VERSION}', 'Accept': 'application/vnd.github+json'})
        self.current = current
        self.release = None
        self._guard = threading.Lock()
        self._operation = threading.Lock()
        self._status = {'state': 'idle', 'current_version': current, 'message': 'Verificando atualizações ao iniciar.', 'progress': 0}

    def _set(self, **values):
        with self._guard:
            self._status.update(values)

    def status(self):
        with self._guard:
            return dict(self._status)

    def check(self):
        if not self._operation.acquire(blocking=False):
            return self.status()
        try:
            self.release = None
            self._set(state='checking', message='Consultando Releases do GitHub.', latest_version=None, notes='', progress=0)
            response = self.client.get(API)
            if response.status_code == 404:
                self._set(state='no_release', message='Nenhuma versão publicada ainda.')
            else:
                response.raise_for_status()
                self.release = parse_release(response.json())
                available = version_tuple(self.release.version) > version_tuple(self.current)
                self._set(state='available' if available else 'current', latest_version=self.release.version,
                          notes=self.release.notes, message='Nova versão disponível.' if available else 'Você está na versão mais recente.')
        except httpx.HTTPError:
            self._set(state='offline', message='Não foi possível consultar o GitHub. Tente novamente mais tarde.')
        except (ValueError, KeyError, TypeError):
            self._set(state='error', message='A release publicada não contém uma atualização válida.')
        finally:
            self._operation.release()
        return self.status()

    def download(self):
        with self._operation:
            release = self.release
            if release is None or version_tuple(release.version) <= version_tuple(self.current):
                raise ValueError('Não há versão mais recente disponível.')
            self.directory.mkdir(parents=True, exist_ok=True)
            target = self.directory / release.name
            partial = target.with_suffix('.part')
            self._set(state='downloading', message='Baixando e verificando o instalador.', progress=0)
            try:
                # Bound the checksum response as well as the executable.
                with self.client.stream('GET', release.checksum_url) as response:
                    response.raise_for_status()
                    checksum = b''
                    for chunk in response.iter_bytes():
                        checksum += chunk
                        if len(checksum) > 1024:
                            raise ValueError('Checksum inválido.')
                fields = checksum.decode('ascii').strip().split()
                if not fields or not re.fullmatch('[a-fA-F0-9]{64}', fields[0]):
                    raise ValueError('Checksum inválido.')
                expected = fields[0].lower()
                total = 0
                digest = hashlib.sha256()
                with self.client.stream('GET', release.url) as response:
                    response.raise_for_status()
                    with partial.open('wb') as output:
                        for chunk in response.iter_bytes(256 * 1024):
                            total += len(chunk)
                            if total > release.size:
                                raise ValueError('Instalador excede o tamanho publicado.')
                            output.write(chunk)
                            digest.update(chunk)
                            self._set(progress=round(total * 100 / release.size))
                if total != release.size or digest.hexdigest() != expected:
                    raise ValueError('Falha de integridade no instalador.')
                with partial.open('rb') as executable:
                    if executable.read(2) != b'MZ':
                        raise ValueError('Arquivo não é um instalador Windows.')
                partial.replace(target)
                self._set(state='ready', message='Instalador verificado. Preparando backup.', progress=100)
                return target
            except BaseException:
                partial.unlink(missing_ok=True)
                target.unlink(missing_ok=True)
                self._set(state='error', message='Atualização cancelada: falha no download ou na verificação.')
                raise
