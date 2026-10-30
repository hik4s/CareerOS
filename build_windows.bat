@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .buildvenv
call .buildvenv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --clean --noconfirm packaging\CareerOS.spec || exit /b 1
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (echo Instale Inno Setup 6 para gerar o instalador.& exit /b 2)
"%ISCC%" packaging\CareerOS.iss || exit /b 1
echo Instalador criado em installer\CareerOS-Setup-0.6.0.exe
