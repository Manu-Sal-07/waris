@echo off
rem Double-click to start the Waris demo UI (opens http://localhost:8501). Uses the project's own Python.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment missing. Run:  python -m venv .venv ^&^& .venv\Scripts\python -m pip install -r requirements.txt
  pause & exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app\streamlit_app.py --server.port 8501
pause
