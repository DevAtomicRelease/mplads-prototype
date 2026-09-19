@echo off
rem Double-click to launch MPLADS-GUARD (PS 26102). Builds if needed, then opens the app.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
