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
for /f %%V in ('python -c "from app.version import VERSION; print(VERSION)"') do set "CAREER_OS_VERSION=%%V"
if not defined CAREER_OS_VERSION exit /b 1
"%ISCC%" /DMyAppVersion=%CAREER_OS_VERSION% packaging\CareerOS.iss || exit /b 1
echo Instalador criado em installer\CareerOS-Setup-%CAREER_OS_VERSION%.exe
