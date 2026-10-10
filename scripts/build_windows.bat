@REM Created: 2026-10-10 10:39 JST
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
python -m pip install -r requirements-windows.txt || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ChartRecorder scripts\tray_launcher.py || exit /b 1
if not exist "dist\setting.yaml" copy "setting.yaml" "dist\setting.yaml" >nul
if not exist "dist\setting.yaml" (echo ERROR: Failed to copy setting.yaml. & exit /b 1)
echo Built: dist\ChartRecorder.exe
endlocal
