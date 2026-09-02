@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" bootstrap.py
  exit /b %errorlevel%
)
where py >nul 2>nul
if %errorlevel%==0 (
  py bootstrap.py
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python bootstrap.py
  exit /b %errorlevel%
)
echo.
echo Python 3.11 or newer was not found.
echo Install it from https://www.python.org/downloads/windows/
echo During setup, enable "Add python.exe to PATH", then run START.bat again.
pause
exit /b 1
