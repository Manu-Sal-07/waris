# Review demo helper (PowerShell).  Usage:  .\scripts\demo.ps1 [main|resume|offline|memory|tests]
param([string]$Mode = "main")
$root = Join-Path $PSScriptRoot ".."
function Run($args_) { cmd /c "cd /d `"$root`" && set PYTHONIOENCODING=utf-8&& .venv\Scripts\python.exe $args_" }
switch ($Mode) {
  "main"    { Run "-m waris.run --case meena --fresh --forget" }
  "offline" { Run "-m waris.run --case meena --fresh --forget --no-llm" }
  "resume"  { Run "-m waris.run --case meena --fresh --forget --exit-at-pause"; Write-Host "`n--- process 'killed'. restarting ---`n"; Run "-m waris.run --case meena" }
  "memory"  { Run "-m waris.run --case meena --fresh" }
  "tests"   { Run "-m pytest -q" }
}
