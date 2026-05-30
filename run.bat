@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe minimal_agent.py
) else (
    python minimal_agent.py
)
