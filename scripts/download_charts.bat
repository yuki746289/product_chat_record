@REM Created: 2026-10-09 22:09 JST
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
where gh >nul 2>&1 || (echo ERROR: GitHub CLI not found. & exit /b 1)
python -m src.local_download --config setting.yaml
if errorlevel 1 (echo ERROR: Download failed. & exit /b 1)
endlocal
