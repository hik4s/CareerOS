@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.11 ou superior e marque Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv (
  echo [1/4] Criando ambiente...
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
if not exist .venv\.deps_ok (
  echo [2/4] Instalando dependencias...
  python -m pip install --upgrade pip
  pip install -r requirements.txt || goto :error
  type nul > .venv\.deps_ok
)
if not exist data\career_os.db (
  echo [3/4] Criando perfil inicial...
  python scripts\seed.py
)
echo [4/4] Abrindo Career OS...
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto :eof
:error
echo Falha na instalacao. Veja as mensagens acima.
pause
exit /b 1
