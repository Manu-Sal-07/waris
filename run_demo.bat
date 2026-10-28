@echo off
rem Double-click for the terminal demo (live run, asks you y/n).
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m waris.run --case meena --fresh --forget
pause
