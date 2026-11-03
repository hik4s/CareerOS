"""Build the Windows one-file app and installer: python scripts/build_windows.py."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAPPER_URL = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def write_checksum(installer: Path) -> Path:
    checksum = installer.with_suffix(installer.suffix + '.sha256')
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    checksum.write_text(f'{digest}  {installer.name}\n', encoding='ascii')
    return checksum


def main() -> None:
    if sys.platform != 'win32':
        raise SystemExit('Build on Windows with Python 3.12 x64 and Inno Setup 6.')
    version = runpy.run_path(str(ROOT / 'app/version.py'))['VERSION']
    tag = os.environ.get('GITHUB_REF', '')
    if tag.startswith('refs/tags/') and tag != f'refs/tags/v{version}':
        raise SystemExit(f'Tag must match v{version}')
    bootstrapper = ROOT / 'packaging/vendor/MicrosoftEdgeWebview2Setup.exe'
    bootstrapper.parent.mkdir(parents=True, exist_ok=True)
    if not bootstrapper.exists():
        urllib.request.urlretrieve(BOOTSTRAPPER_URL, bootstrapper)
    # Validate every cached/downloaded binary, not merely HTTPS transport.
    run('powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
        "$s=Get-AuthenticodeSignature -LiteralPath 'packaging/vendor/MicrosoftEdgeWebview2Setup.exe'; "
        "if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation(?:,|$)') "
        "{ throw 'WebView2 bootstrapper must have a valid Microsoft Authenticode signature' }")
    run(sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', 'packaging/CareerOS.spec')
    iscc = shutil.which('ISCC.exe')
    if not iscc:
        for variable in ('ProgramFiles(x86)', 'ProgramFiles'):
            candidate = Path(os.environ.get(variable, 'C:/Program Files')) / 'Inno Setup 6/ISCC.exe'
            if candidate.exists():
                iscc = str(candidate)
                break
    if not iscc:
        raise SystemExit('Install Inno Setup 6 (ISCC.exe).')
    run(iscc, f'/DMyAppVersion={version}', 'packaging/CareerOS.iss')
    installer = ROOT / f'installer/CareerOS-Setup-{version}.exe'
    checksum = write_checksum(installer)
    print(f'Created {installer}\nCreated {checksum}')


if __name__ == '__main__':
    main()
