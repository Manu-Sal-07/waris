# Waris: an agentic AI system for unclaimed inheritance recovery

> Agentic AI (26CD7PEAAI), BMS College of Engineering. Team: Srijan C Vachadmath (lead), Chirag T, Manohara Salmani, Mohammed Arshaq.
> **Advisory only.** Waris never moves money, never files a claim, never decides legal heirship. All data is synthetic.

For each asset a deceased person left behind (bank deposit, life insurance, shares) Waris answers one question:
**is the claim ready to file, and if not, exactly what is missing?** Status is `READY`, `MISSING_ITEMS` or `NEEDS_HUMAN_REVIEW`.

## What is built (Review 2 slice)
A real LangGraph system with a Supervisor and four agents, running Meena's case end to end:

| Agent | Pattern | Does |
|---|---|---|
| Supervisor | plan-and-execute | validates input, plans one task per asset type, routes, enforces limits, pauses for the family |
| Tracer | ReAct | LLM picks the next portal; code scores identity (name + DOB + city); namesakes are rejected |
| Rules Expert | corrective RAG | retrieve → grade fit → re-query (≤2) → abstain ("I don't know") |
| Builder | | cited checklist of `DOC_*` codes, pydantic-validated |
| Verifier | reflection / critic | fixed checks V1–V5, sends weak work back with a reason (≤6 rounds) |

Also: human-in-the-loop interrupts, SQLite checkpointing (kill and resume), long-term case-file memory,
PII masking, prompt-injection guard, hard limits, Langfuse + local HTML trace, scorecard against an answer key.

**LLM is used only for small decisions** (which tool next, borderline rule grading). Status, citations, identity score and limits are fixed code, so results are reproducible and testable.

## Demo UI
`.\scripts\ui.ps1` (or `python -m streamlit run app/streamlit_app.py`) opens http://localhost:8501 with three tabs:
**Run a case** (live agent timeline, family questions as buttons, claim packs, scorecard, crash-and-resume button),
**Rules & RAG explorer** (the corpus, retrieval, fit grading) and **Graph & trace**.

## Run it (Windows, PowerShell or Git Bash)
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
ollama pull llama3.1:8b                       # optional: without it Waris uses deterministic fallbacks
.venv\Scripts\python -m waris.run --case meena --fresh --forget
```
The mock portals start automatically. Answer the two prompts with `y`.

| Command | Shows |
|---|---|
| `python -m waris.run --case meena --fresh --forget` | the full live run |
| `... --no-llm` | same run, no LLM (demo-safe) |
| `... --answers y,y` | scripted human answers (no typing) |
| `... --exit-at-pause` then `python -m waris.run --case meena` | **durable resume**: process stops at the family question, restart continues from the checkpoint |
| `python -m waris.run --case meena --fresh` | **memory**: the family's earlier answer is reused, not asked again |
| `python -m waris.run --show-graph` | the graph as Mermaid |
| `python -m pytest -q` | 18 tests |

Open `traces/meena.html` for the trace of any run. Optional Langfuse: `docker compose up -d`, then http://localhost:3000
(login `waris@example.com` / `waris-demo-pass`; keys are pre-seeded in `.env.example`).

## Layout
```
waris/            state.py graph.py run.py config.py guardrails.py tracing.py memory.py llm.py doc_codes.py
  agents/         supervisor tracer rules_expert builder verifier finalize human
  tools/          portals name_match retrieval status
portals/app.py    mock bank / insurer / registry (FastAPI + SQLite)
data/             rules/*.md (cited rule corpus) · cases/meena/{input,answer_key}.json · seed_portals.py
eval/metrics.py   asset recall, wrong-person matches, status accuracy, checklist P/R, citation coverage, abstention
tests/            18 tests incl. an end-to-end graph run
docs/             how_waris_works.html (open this to learn the flow), design document, slides, figures, demo script, viva Q&A  (python docs/build_*.py)
```

## Limits (every loop is bounded)
Verifier rounds ≤ 6 · RAG re-queries ≤ 2 per asset · Tracer steps ≤ 8 · LLM calls ≤ 40 per case · tool timeout 10 s.
Hitting a limit makes the asset `NEEDS_HUMAN_REVIEW`. The same Verifier failure twice escalates the asset.

## Not yet built (planned for Review 3/4)
OCR of scans, letter drafting, Streamlit UI, 60-case generator and eval harness, LLM-as-judge, A/B + ablation experiments.

## Rule corpus note
Rule files in `data/rules/` are written from public RBI / IRDAI / IEPF procedure *types* and marked `verified: illustrative`.
They are not legal advice. One situation (insurance claim where the nominee has died) is deliberately uncovered so the abstention path is testable.
