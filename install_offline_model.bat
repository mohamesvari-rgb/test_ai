@echo off
rem Download the local model for OFFLINE mode (needs Ollama installed).
rem   install_offline_model.bat                      default model (qwen3.5:9b)
rem   install_offline_model.bat -Model qwen3.5:4b    smaller / faster
rem   install_offline_model.bat -Gguf D:\file.gguf -Model my-model
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_offline_model.ps1" %*
echo.
pause
