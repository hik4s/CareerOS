@echo off
setlocal
cd /d "%~dp0"
python scripts\build_windows.py
exit /b %errorlevel%
