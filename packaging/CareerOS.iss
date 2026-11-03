#define MyAppName "Career OS"
#ifndef MyAppVersion
  #error Supply MyAppVersion from app/version.py using scripts/build_windows.py
#endif
#define MyAppExeName "CareerOS.exe"
[Setup]
AppId={{A76049CB-A3F5-4BDE-A031-CAREEROS0400}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Career OS
DefaultGroupName=Career OS
OutputDir=..\installer
OutputBaseFilename=CareerOS-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
WizardStyle=modern
CloseApplications=no
[Files]
Source: "..\dist\CareerOS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "extension-guide.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy
[Icons]
Name: "{autoprograms}\Career OS"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Career OS - instalar extensao"; Filename: "{app}\extension-guide.html"
Name: "{autoprograms}\Career OS - pasta da extensao"; Filename: "{app}\extension"
Name: "{autodesktop}\Career OS"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Career OS"; Flags: nowait postinstall skipifsilent; Check: not IsCareerUpdate
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: IsCareerUpdate
[Code]
function IsCareerUpdate: Boolean;
var I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), '/CAREEROSUPDATE') = 0 then Result := True;
end;

function InstalledVersion: String;
begin
  Result := '';
  RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A76049CB-A3F5-4BDE-A031-CAREEROS0400}_is1', 'DisplayVersion', Result);
end;

function InitializeSetup: Boolean;
var Existing: String; OldVersion, NewVersion: Int64;
begin
  Existing := InstalledVersion;
  Result := True;
  if Existing <> '' then begin
    if not StrToVersion(Existing, OldVersion) then Result := False
    else if not StrToVersion('{#MyAppVersion}', NewVersion) then Result := False
    else Result := ComparePackedVersion(OldVersion, NewVersion) <= 0;
  end;
  if not Result then MsgBox('Uma versao mais recente do Career OS ja esta instalada.', mbError, MB_OK);
end;

function HasWebView2: Boolean;
var V: String;
begin
  { Microsoft distribution docs: 32-bit registry view on 64-bit Windows. }
  Result := RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0');
  if not Result then
    Result := RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', V) and (V <> '') and (V <> '0.0.0.0');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Attempts, ExitCode: Integer;
begin
  Result := '';
  Attempts := 0;
  while CheckForMutexes('Local\CareerOS.Desktop') and (Attempts < 120) do begin
    Sleep(500);
    Attempts := Attempts + 1;
  end;
  if CheckForMutexes('Local\CareerOS.Desktop') then begin
    Result := 'Feche o Career OS e tente novamente.';
    Exit;
  end;
  if not HasWebView2 then begin
    ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
    if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then begin
      Result := 'Nao foi possivel iniciar a instalacao do WebView2.';
      Exit;
    end;
    if not HasWebView2 then Result := 'WebView2 nao foi instalado. Conecte-se a internet e tente novamente.';
  end;
end;
