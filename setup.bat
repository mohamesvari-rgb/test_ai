@echo off
rem One-time setup: Python runtime + packages + .env
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" %*
echo.
pause
