@REM Created: 2026-10-14 JST
@REM Build ChartRecorder.exe and a self-contained setup.exe on Windows.
@REM setup.exe bundles only public config and the EXE; never keyring secrets.
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
if not exist "system.yaml" (echo ERROR: system.yaml not found. & exit /b 1)
call scripts\build_windows.bat || exit /b 1
if not exist "dist\ChartRecorder.exe" (echo ERROR: main ChartRecorder.exe build failed. & exit /b 1)
python -m PyInstaller --noconfirm --clean --onefile --windowed --name setup --distpath dist --workpath build\setup --specpath build\setup_spec --add-binary "%CD%\dist\ChartRecorder.exe;payload" --add-data "%CD%\setting.yaml;payload" --add-data "%CD%\system.yaml;payload" scripts\setup_chartrecorder.py || exit /b 1
if not exist "dist\setup.exe" (echo ERROR: setup.exe not found after build. & exit /b 1)
echo Built: dist\setup.exe
echo Place an optional system.yaml next to setup.exe to customize installation destination.
endlocal
