@echo off
REM Double-click this file to start the Local Agent Framework's web UI.
REM It opens http://127.0.0.1:8765 in your default browser automatically.
cd /d "%~dp0"
local-agent.exe --serve
pause
