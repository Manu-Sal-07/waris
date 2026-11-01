#!/usr/bin/env bash
# Full evaluation chain (about 2 hours with the local LLM). Every run starts from the case's PROOF DOCUMENTS.
cd "$(dirname "$0")/.."
PY=.venv/Scripts/python
export PYTHONIOENCODING=utf-8
$PY -m eval.run_eval --split all --repeats 3 --out results/main
$PY -m eval.run_eval --cases-dir data/cases_unseen --split all --repeats 1 --out results/unseen
$PY -m eval.run_eval --cases-dir data/cases_stress --split all --repeats 1 --out results/stress
for r in main unseen stress; do $PY -m eval.analyze results/$r > /dev/null; done
$PY -m eval.judge validate
$PY -m eval.judge score results/main
for r in main unseen stress; do $PY -m eval.analyze results/$r > /dev/null; done
echo ALL_DONE
