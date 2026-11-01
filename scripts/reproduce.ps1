# Reproduce everything from a clean clone (Windows PowerShell).   .\scripts\reproduce.ps1 [-Quick]
#   -Quick : 1 repetition, held-out test cases only (about 10 minutes) instead of the full 60 cases x 3 repetitions (about 2 hours)
param([switch]$Quick)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { python -m venv .venv; & $py -m pip install -r requirements.txt }
Write-Host "1/6 models (Ollama must be running)"; ollama pull llama3.1:8b; ollama pull nomic-embed-text
Write-Host "2/6 generate the 60 synthetic families: shared portal database, proof folders in demo_proofs/, answer keys; self-check with the real OCR"
& $py -m data.generate_cases
& $py -m data.generate_cases --seed 424242 --out data/cases_unseen        # a fresh draw nobody tuned on
& $py -m data.generate_cases --seed 31337 --out data/cases_stress --set stress
Write-Host "3/6 tests"; & $py -m pytest -q
$split = if ($Quick) { "test" } else { "all" }; $reps = if ($Quick) { 1 } else { 3 }
Write-Host "4/6 evaluation from the proof documents: full Waris, one-pass baseline, no Verifier, no grading, LLM off"
& $py -m eval.run_eval --split $split --repeats $reps --out results/main
if (-not $Quick) {
  & $py -m eval.run_eval --cases-dir data/cases_unseen --split all --repeats 1 --out results/unseen
  & $py -m eval.run_eval --cases-dir data/cases_stress --split all --repeats 1 --out results/stress
}
Write-Host "5/6 tables, plots, failure analysis"
foreach ($r in "main", "unseen", "stress") { if (Test-Path "results/$r/runs.jsonl") { & $py -m eval.analyze "results/$r" | Out-Null } }
Write-Host "6/6 LLM-judge validation and letter scoring"; & $py -m eval.judge validate; & $py -m eval.judge score results/main; & $py -m eval.analyze results/main | Out-Null
Write-Host "Done. Open results\main\summary.md, then run:  .\run_ui.bat   and upload the images of any folder under demo_proofs\"
