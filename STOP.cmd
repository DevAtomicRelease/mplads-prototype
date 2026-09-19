@echo off
rem Stop the MPLADS-GUARD process started by run.ps1 / START.cmd (only that process).
setlocal enabledelayedexpansion
set "PIDFILE=%~dp0six_source\local\.serve.pid"
if not exist "%PIDFILE%" ( echo No running MPLADS-GUARD process was recorded. & exit /b 0 )
set /p SPID=<"%PIDFILE%"
taskkill /PID !SPID! /F >nul 2>&1
del "%PIDFILE%" >nul 2>&1
echo Stopped MPLADS-GUARD ^(PID !SPID!^).
