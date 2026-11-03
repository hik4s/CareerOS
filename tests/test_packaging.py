"""Cross-platform contract checks; Windows runtime acceptance remains required."""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_checksum_sidecar_matches_updater_contract(tmp_path):
    spec = importlib.util.spec_from_file_location('build_windows', ROOT / 'scripts/build_windows.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    installer = tmp_path / 'CareerOS-Setup-0.7.0.exe'
    installer.write_bytes(b'installer fixture')
    checksum = module.write_checksum(installer)
    assert checksum.name == installer.name + '.sha256'
    assert checksum.read_text() == hashlib.sha256(installer.read_bytes()).hexdigest() + '  ' + installer.name + '\n'


def test_installer_preserves_identity_and_user_data():
    script = (ROOT / 'packaging/CareerOS.iss').read_text()
    assert 'AppId={{A76049CB-A3F5-4BDE-A031-CAREEROS0400}' in script
    assert r'DefaultDirName={localappdata}\Programs\Career OS' in script
    assert 'PrivilegesRequired=lowest' in script
    assert '[UninstallDelete]' not in script
    assert '[InstallDelete]' not in script
    assert 'ComparePackedVersion(OldVersion, NewVersion) <= 0' in script
    assert "CheckForMutexes('Local\\CareerOS.Desktop')" in script
    assert "'/CAREEROSUPDATE'" in script
    assert 'Check: IsCareerUpdate' in script
    assert 'extension-guide.html' in script


def test_release_build_validates_and_remains_draft():
    workflow = (ROOT / '.github/workflows/windows-installer.yml').read_text()
    builder = (ROOT / 'scripts/build_windows.py').read_text()
    assert '--draft --verify-tag' in workflow
    assert 'python -m pytest -q' in workflow
    assert 'Get-AuthenticodeSignature' in builder
    assert 'Microsoft Corporation' in builder
    assert "tag != f'refs/tags/v{version}'" in builder
