@echo off
rem Start the demo: web app + (if installed) the local Ollama engine.
rem   start.bat            open in a clean app window
rem   start.bat -Browser   open in a normal browser tab
title Scientific Evaluation Agent
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
if errorlevel 1 pause
