@echo off
powershell.exe -NoProfile -File "%~dp0START_PROJECT.ps1"
if errorlevel 1 pause
