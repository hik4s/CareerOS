$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut((Join-Path $desktop 'Career OS.lnk'))
$sc.TargetPath = (Join-Path $root 'start_career_os.bat')
$sc.WorkingDirectory = $root
$sc.Description = 'Abrir Career OS'
$sc.Save()
Write-Host 'Atalho criado na Area de Trabalho.'
