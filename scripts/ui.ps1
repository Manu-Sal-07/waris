# Starts the Waris demo UI at http://localhost:8501. Routed through cmd so PowerShell 5.1 does not paint
# Streamlit's normal stderr banner red (it looks like an error but is not).
$root = Join-Path $PSScriptRoot ".."
cmd /c "cd /d `"$root`" && set PYTHONIOENCODING=utf-8&& .venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.port 8501"
