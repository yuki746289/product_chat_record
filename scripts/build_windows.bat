@REM Created: 2026-10-10 10:39 JST
@REM Updated: 2026-10-10 JST (repository-root default configuration)
@REM Updated: 2026-10-14 JST (optional versioned staging output path)
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
if not exist "setting.yaml" (echo ERROR: Repository setting.yaml is missing. & exit /b 1)
python -m pip install -r requirements-windows.txt || exit /b 1
if defined CHARTRECORDER_DIST_DIR (
  set "OUTPUT_DIR=%CHARTRECORDER_DIST_DIR%"
) else (
  set "OUTPUT_DIR=dist"
)
python -m PyInstaller --noconfirm --clean --onefile --windowed --collect-submodules keyring.backends --name ChartRecorder --distpath "%OUTPUT_DIR%" scripts\tray_launcher.py || exit /b 1
if not exist "%OUTPUT_DIR%\ChartRecorder.exe" (echo ERROR: EXE missing. & exit /b 1)
echo Built: %OUTPUT_DIR%\ChartRecorder.exe
echo Using external setting.yaml (no credentials are embedded)
endlocal
