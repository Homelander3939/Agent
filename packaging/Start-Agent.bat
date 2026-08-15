@echo off
REM Double-click this file to start the Local Agent Framework's web UI.
REM It opens http://127.0.0.1:8765 in your default browser automatically.
cd /d "%~dp0"

REM First-run convenience: create config.yaml/.env from the bundled
REM examples so a new Windows user doesn't have to touch a terminal to
REM get going. Edit config.yaml afterwards to flip on LM Studio
REM (lmstudio.enabled: true) or a cloud fallback.
if not exist "config.yaml" (
    if exist "config\config.example.yaml" (
        copy /y "config\config.example.yaml" "config.yaml" >nul
        echo Created config.yaml from the example. Edit it to enable LM Studio or a cloud provider.
    )
)
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
    )
)

local-agent.exe --serve
pause
