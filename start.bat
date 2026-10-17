@echo off
setlocal
cd /d "%~dp0"

rem Normal launch is ALWAYS Thermal Chaos, even if camera mode was set in
rem an older shell. Only the dedicated Eagle Eye launcher opts in.
set "THERMAL_CHAOS_CAMERA=0"
set "THERMAL_CHAOS_PAGE=http://127.0.0.1:8765/"
if /I "%~1"=="--eagle-eye" (
  set "THERMAL_CHAOS_CAMERA=1"
  set "THERMAL_CHAOS_PAGE=http://127.0.0.1:8765/eagle-eye"
)

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
if not exist .venv\Scripts\python.exe (
  %PY% -m venv .venv
  if errorlevel 1 (echo Python 3 is required. & pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. & pause & exit /b 1)
start "" "%THERMAL_CHAOS_PAGE%"
.venv\Scripts\python.exe app.py
pause
