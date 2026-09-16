@echo off
powershell.exe -NoProfile -File "%~dp0STOP_PROJECT.ps1"
if errorlevel 1 pause
