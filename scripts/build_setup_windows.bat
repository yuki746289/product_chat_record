@REM Created: 2026-10-14 JST
@REM Build ChartRecorder.exe and a self-contained setup.exe on Windows.
@REM setup.exe bundles only public config and the EXE; never keyring secrets.
@REM Updated: 2026-10-14 JST (build app in versioned release folder, no EXE overwrite)
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
if not exist "system.yaml" (echo ERROR: system.yaml not found. & exit /b 1)
@REM Build inside a versioned directory so the running dist/ChartRecorder.exe is never touched.
for /f "delims=" %%V in ('python -m scripts.versioning') do set "RELEASE_ID=%%V"
if not defined RELEASE_ID (echo ERROR: release version could not be read. & exit /b 1)
set "RELEASE_DIR=%CD%\dist\releases\%RELEASE_ID%"
set "CHARTRECORDER_DIST_DIR=%RELEASE_DIR%"
call scripts\build_windows.bat || exit /b 1
set "CHARTRECORDER_DIST_DIR="
if not exist "%RELEASE_DIR%\ChartRecorder.exe" (echo ERROR: versioned ChartRecorder.exe missing. & exit /b 1)
echo %RELEASE_ID%>"%RELEASE_DIR%\release-version.txt"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name setup --distpath dist --workpath build\setup --specpath build\setup_spec --add-binary "%RELEASE_DIR%\ChartRecorder.exe;payload" --add-data "%CD%\setting.yaml;payload" --add-data "%CD%\system.yaml;payload" --add-data "%RELEASE_DIR%\release-version.txt;payload" scripts\setup_chartrecorder.py || exit /b 1
if not exist "dist\setup.exe" (echo ERROR: setup.exe not found after build. & exit /b 1)
echo Built: dist\setup.exe
echo Place an optional system.yaml next to setup.exe to customize installation destination.
endlocal
