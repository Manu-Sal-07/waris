# Waris: an agentic AI system for unclaimed inheritance recovery

> Agentic AI (26CD7PEAAI), BMS College of Engineering. Team: Srijan C Vachadmath (lead), Chirag T, Manohara Salmani, Mohammed Arshaq.
> **Advisory only.** Waris never moves money, never files a claim, never decides legal heirship. All data is synthetic.

For each asset a deceased person left behind (bank deposit, life insurance, shares) Waris answers one question:
**is the claim ready to file, and if not, exactly what is missing?** Status is `READY`, `MISSING_ITEMS` or `NEEDS_HUMAN_REVIEW`,
and every checklist item cites the rule it came from.

## What is built
A LangGraph system with a Supervisor and four specialist agents, a document-intake step and a letter writer:

| Part | Pattern | Does |
|---|---|---|
| Supervisor | plan-and-execute | validates input, plans one task per asset type, routes, enforces limits, pauses for the family |
| `doc_intake` | tool use (OCR) | reads the family's scans with an offline OCR; readable scans count as held documents, unreadable ones never do, documents that disagree are flagged (never resolved), injection text inside a scan is dropped |
| Tracer | ReAct | the LLM picks the next portal; code scores identity (name + DOB + city) under every name the family knows; namesakes are rejected; medium matches go to the family |
| Rules Expert | corrective RAG | retrieve → grade fit → re-query (≤ 2, excluding rejected rules) → abstain ("I don't know") |
| Builder | | cited checklist of `DOC_*` codes, pydantic-validated |
| Verifier | reflection / critic | fixed checks V1–V5, sends weak work back with a reason (≤ 6 rounds) |
| `draft_letters` | | a validated claim letter for every claimable asset (the family reviews and sends it) |

Also: human-in-the-loop interrupts, SQLite checkpointing (kill and resume), long-term case-file memory (also across sessions), PII masking,
prompt-injection guard, hard limits on every loop, Langfuse + local HTML traces.
**The LLM makes only small decisions** (which tool next, borderline rule fit, a letter's opening paragraph, all validated). Status, citations,
identity scores and limits are fixed code, so results are reproducible and testable.

## The benchmark and the evidence
* `python -m data.generate_cases` builds **60 seeded synthetic cases** (15 easy, 25 medium, 20 hard; 40 dev / 20 held-out test): name variants
  (initials, spelling, transliteration, order, maiden name), namesakes, partial information, no assets, several accounts, nominee vs legal heir,
  small vs large amounts, joint accounts, missing and conflicting documents, rules missing from the corpus, a document arriving in a later session,
  clean / rotated / blurry / faded scans, an injection attack in a scan, and portal failures. Every scenario appears at least 3 times.
  Truth is generated first; the answer keys are written by the generator, never by an LLM. See `docs/DATA_AND_RULES_GUIDE.md`.
* `python -m eval.run_eval` runs every case under five variants, 3 repetitions each (different temperature and seed):
  **full Waris**, **one-pass baseline** (same tools, no identity policy, grading, Verifier or human questions), **no Verifier**, **no grading / re-query**,
  and **Waris with the LLM off**. `python -m eval.analyze results/main` writes tables, plots and a failure analysis;
  `python -m eval.judge` validates an LLM judge for letters and scores every letter.
* Results: **`results/main/summary.md`** (held-out test split = headline numbers, dev split and all 60 reported separately),
  `results/main/figures/`, `results/main/failures.md`, `results/judge/`. The family is simulated by a scripted oracle that answers from the
  answer key; this is stated in every result.

### Headline results (held-out 20 test cases, 3 repetitions; full tables in `results/main/summary.md`)
| | One-pass baseline | Waris − grading | Waris − Verifier | Waris, LLM off | **Full Waris** |
|---|---|---|---|---|---|
| Status accuracy | 73.1 % | 92.3 % | 100 % | 100 % | **100 %** |
| Checklist F1 | 57.8 % | 69.0 % | 97.1 % | 100 % | **100 %** |
| Cases fully correct | 20 % | 35 % | 70 % | 100 % | **100 %** |
| Wrong-person claims | 4 | 0 | 0 | 0 | **0** |
| Family questions asked when needed | 0 % | 100 % | 100 % | 100 % | **100 %** |

* Over all 60 cases the baseline claims a namesake's money **12 times**; full Waris never does.
* **Fresh draw:** `data/cases_unseen` (new seed, generated after the decision code was frozen): full Waris again fully correct; baseline 72.4 % status accuracy, 8 wrong-person claims.
* **Verifier stress set** (`data/cases_stress`: the family holds everything except the name affidavit): without the Verifier the status is wrong in every case (0 % vs 100 %).
* **LLM off = identical accuracy.** The accuracy comes from the loops and fixed code; the LLM adds flexible tool choice and letter wording (about 4 calls a case).
* **Letters:** deterministic reference checker 4.76 / 5 for full Waris vs 3.66 for the baseline; the LLM judge is validated against that checker (91 % agreement, κ 0.61).
* Findings that changed the system: the first LLM letters invented "matured on <date>" (caught by the judge, validator tightened); joint-holder cases abstained until the re-query wording was rewritten; maiden-name records were missed until the Tracer searched under every name the family knows.

## Run it (Windows, PowerShell or Git Bash)
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
ollama pull llama3.1:8b ; ollama pull nomic-embed-text      # optional: without them Waris uses deterministic fallbacks
.venv\Scripts\python -m data.generate_cases                  # 60 cases (already committed; reproducible)
.venv\Scripts\python -m waris.run --case h07 --fresh --forget --answers y,y
.\run_ui.bat                                                  # the demo UI (http://localhost:8501)
```
The mock portals start automatically. `python -m waris.run --list-cases` lists the cases and what each one tests; `meena` is the hand-built demo case.

| Command | Shows |
|---|---|
| `python -m waris.run --case meena --fresh --forget` | the classic demo: name variant, rule graded unfit, family question |
| `... --case h07 --no-llm` | a case with scans: OCR, a document conflict, a namesake, an initials variant |
| `... --case m15 --fresh --forget` then `... --case m15 --session2` | a document arrives in a later session; the family's earlier answer is remembered |
| `... --exit-at-pause` then rerun without `--fresh` | **durable resume** from the SQLite checkpoint |
| `python -m waris.run --show-graph` | the graph as Mermaid |
| `python -m pytest -q` | 100+ tests (`WARIS_TEST_ALL=1` runs all 60 cases end to end) |
| `.\scripts\reproduce.ps1 [-Quick]` | everything: generate, test, evaluate, analyse, judge |

The UI has four tabs: **Run a case** (live timeline, scans with OCR results, family questions as buttons, claim packs, letters, scorecard, crash-and-resume,
session 2), **Rules & RAG explorer**, **Evaluation (60 cases)** and **Graph & trace**. Traces are written to `traces/` and, with
`docker compose up -d`, to Langfuse at http://localhost:3001 (login `waris@example.com` / `waris-demo-pass`; keys pre-seeded in `.env.example`).

## Layout
```
waris/            state graph run config guardrails tracing memory llm doc_codes baseline
  agents/         supervisor doc_intake tracer rules_expert builder verifier finalize letters human
  tools/          portals name_match retrieval status ocr
portals/app.py    mock bank / insurer / registry (FastAPI + SQLite), per-case sandboxes, injectable faults
data/             generate_cases.py scans.py rules/*.md (11 cited rules) cases/{meena, e01..h20}/ split.json index.json
eval/             metrics run_eval analyze judge
results/          main/ (runs, summary, figures, failures, letters)  judge/ (validation)
tests/            core, benchmark (all 60 cases), UI
app/              Streamlit demo UI
docs/             explainer, guides, speaker scripts, Review-2 deck and design document
```

## Limits (every loop is bounded)
Verifier rounds ≤ 6 · RAG re-queries ≤ 2 per asset · Tracer steps ≤ 8 · LLM calls ≤ 40 per case · tool timeout 10 s, 2 retries.
Hitting a limit makes the asset `NEEDS_HUMAN_REVIEW`; the same Verifier failure twice escalates it.

## Honest scope
* All data is synthetic and the portals are mocks; no real institution is connected and none was contacted.
* The 11 rules follow public RBI / IRDAI / IEPF procedure types but are marked `verified: illustrative` (the Rs 5 lakh small/large split is illustrative).
  Waris gives no legal advice.
* The benchmark was written by the team for this system, so near-perfect scores on it show the machinery works end to end, not that it generalises to real
  portals. The one-pass baseline and the ablations show what each agentic component contributes on the same cases.
* The LLM judge is checked against a deterministic reference checker and a template for the team's own marks (`results/judge/human_marks_template.csv`).
