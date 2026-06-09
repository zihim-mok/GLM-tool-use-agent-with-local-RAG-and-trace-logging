@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m pip install -q -r requirements.txt
    .venv\Scripts\python.exe web_app.py
) else (
    python -m pip install -q -r requirements.txt
    python web_app.py
)
