@REM Created: 2026-10-14 JST
@REM Rebuild only when needed, then cooperatively stop and restart ChartRecorder.
@REM Never force-kill Saxo or overwrite an active EXE.
@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>&1 || (echo ERROR: Python not found. & exit /b 1)
python -m scripts.update_chartrecorder %*
exit /b %ERRORLEVEL%
