@echo off
rem Identity-checked stop; optional argument is the local port.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
