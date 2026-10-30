#define MyAppName "Career OS"
#define MyAppVersion "0.6.0"
#define MyAppExeName "CareerOS.exe"
[Setup]
AppId={{A76049CB-A3F5-4BDE-A031-CAREEROS0400}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Career OS
DefaultGroupName=Career OS
OutputDir=..\installer
OutputBaseFilename=CareerOS-Setup-0.6.0
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
WizardStyle=modern
[Files]
Source: "..\dist\CareerOS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Career OS"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Career OS"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Career OS"; Flags: nowait postinstall skipifsilent
