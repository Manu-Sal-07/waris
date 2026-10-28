# Windows without make? Use the equivalent commands in README.md (or scripts/demo.ps1).
PY = .venv/Scripts/python

setup:
	python -m venv .venv && $(PY) -m pip install -r requirements.txt
data:
	$(PY) -m data.seed_portals
index:
	$(PY) -c "from waris.tools.retrieval import index_rules; index_rules(); print('rules indexed')"
langfuse:
	docker compose up -d
demo:
	$(PY) -m waris.run --case meena --fresh --forget
demo-offline:
	$(PY) -m waris.run --case meena --fresh --forget --no-llm
resume-demo:
	$(PY) -m waris.run --case meena --fresh --forget --exit-at-pause
	$(PY) -m waris.run --case meena
test:
	$(PY) -m pytest -q
docs:
	$(PY) docs/build_figures.py && $(PY) docs/build_pptx.py && $(PY) docs/build_docx.py
