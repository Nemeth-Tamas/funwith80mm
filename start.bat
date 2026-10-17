@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
if not exist .venv\Scripts\python.exe (
  %PY% -m venv .venv
  if errorlevel 1 (echo Python 3 is required. & pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. & pause & exit /b 1)
if "%THERMAL_CHAOS_CAMERA%"=="1" (
  start "" http://127.0.0.1:8765/eagle-eye
) else (
  start "" http://127.0.0.1:8765
)
.venv\Scripts\python.exe app.py
pause
