@REM Created: 2026-10-10 10:39 JST
@REM Updated: 2026-10-10 JST (repository-root default configuration)
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
if not exist "setting.yaml" (echo ERROR: Repository setting.yaml is missing. & exit /b 1)
python -m pip install -r requirements-windows.txt || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --collect-submodules keyring.backends --name ChartRecorder scripts\tray_launcher.py || exit /b 1
echo Built: dist\ChartRecorder.exe
echo Using settings: repository-root setting.yaml (no --config required)
endlocal
