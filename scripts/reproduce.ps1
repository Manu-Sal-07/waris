# Reproduce everything from a clean clone (Windows PowerShell).   .\scripts\reproduce.ps1 [-Quick]
#   -Quick : 1 repetition, held-out test cases only (about 10 minutes) instead of the full 60 cases x 3 repetitions (about 2 hours)
param([switch]$Quick)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { python -m venv .venv; & $py -m pip install -r requirements.txt }
Write-Host "1/6 models (Ollama must be running)"; ollama pull llama3.1:8b; ollama pull nomic-embed-text
Write-Host "2/6 generate the 60 synthetic cases (seeded) and self-check them against the identity policy and the OCR"
& $py -m data.generate_cases
Write-Host "3/6 tests"; & $py -m pytest -q
$split = if ($Quick) { "test" } else { "all" }; $reps = if ($Quick) { 1 } else { 3 }
Write-Host "4/6 evaluation: full Waris, one-pass baseline, no Verifier, no grading, LLM off"
& $py -m eval.run_eval --split $split --repeats $reps --out results/main
Write-Host "5/6 tables, plots, failure analysis"; & $py -m eval.analyze results/main
Write-Host "6/6 LLM-judge validation and letter scoring"; & $py -m eval.judge validate; & $py -m eval.judge score results/main
Write-Host "Done. Open results\main\summary.md, then run:  .\run_ui.bat"
