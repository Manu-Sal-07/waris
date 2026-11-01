# Waris: an agentic AI system for unclaimed inheritance recovery

> Agentic AI (26CD7PEAAI), BMS College of Engineering. Team: Srijan C Vachadmath (lead), Chirag T, Manohara Salmani, Mohammed Arshaq.
> **Advisory only.** Waris never moves money, never files a claim, never decides legal heirship. All data is synthetic.

A family uploads the **proofs** it holds (the deceased's death certificate, the claimant's own ID, a proof of relationship, any forms) and
fills three fields. Waris reads the documents with OCR, builds the case, and for each asset of the deceased (bank deposit, life insurance,
shares) answers one question: **is the claim ready to file, and if not, exactly what is missing?** Status is `READY`, `MISSING_ITEMS` or
`NEEDS_HUMAN_REVIEW`, and every checklist item cites the rule it came from.

## How it works
```
 upload proofs ──► read_documents (OCR) ──► case ──► Supervisor ─► doc_intake ─► Tracer ─► Rules Expert ─► Builder ─► Verifier ─► letters ─► family approves
 (photos/scans)    what is each file?        built      plan        credit /      search     retrieve →      cited       V1–V5       drafts
                   what does it say?         + confirm              flag docs     portals    grade → re-     checklist   send-back
                                                                                  identity   query → abstain             loop
```
| Part | Pattern | Does |
|---|---|---|
| `intake` (before the graph) | tool use (OCR) | works out what each uploaded file is and what it says; builds the case from the death certificate, ID and relationship proof; falls back to what the family types for anything unreadable; the family confirms |
| Supervisor | plan-and-execute | validates the case, plans one task per institution the family asked about, routes, enforces limits, pauses for the family |
| `doc_intake` | tool use (OCR) | readable documents count as held, unreadable ones never do, documents that disagree are flagged (never resolved), injection text inside a document is dropped |
| Tracer | ReAct | the LLM picks the next portal; code scores identity (name + DOB + city) under every name the family knows; namesakes are rejected; medium matches go to the family |
| Rules Expert | corrective RAG | retrieve → grade fit → re-query (≤ 2, excluding rejected rules) → abstain ("I don't know") |
| Builder | | cited checklist of `DOC_*` codes, pydantic-validated |
| Verifier | reflection / critic | fixed checks V1–V5, sends weak work back with a reason (≤ 6 rounds) |
| `draft_letters` | | a validated claim letter for every claimable asset (the family reviews and sends it) |

Also: human-in-the-loop interrupts, SQLite checkpointing (kill and resume), long-term case-file memory (also across sessions), PII masking,
prompt-injection guard, hard limits on every loop, Langfuse + local HTML traces.
**The LLM makes only small decisions** (which tool next, borderline rule fit, a letter's opening paragraph, all validated). Status, citations,
identity scores and limits are fixed code, so results are reproducible and testable.

## Try it (the evaluator's path)
```
.\run_ui.bat                        # opens http://localhost:8501
```
1. Open any folder under **`demo_proofs/`** (named after the deceased and the difficulty, e.g. `sundaram_pillai_hard`, `ramaswamy_subramanian_demo`).
2. In the app, **upload all the images of that folder** (select them all). Waris shows what it recognised and read.
3. Fill the three fields as the folder's `README.txt` says (which assets, claiming as, other names), check the facts, press **Start**.
4. Answer the family question if one appears, approve the release. Folders with a `later/` sub-folder continue with **Add more documents**.

No case is chosen from a list; the case comes from the documents. (A hidden "for developers" panel runs a benchmark case from its structured input.)

## The benchmark and the evidence
* `python -m data.generate_cases` builds **60 seeded synthetic families**: their proof documents (`demo_proofs/`), **one shared portal database**
  that also holds every other family's records, and an answer key. 15 easy, 25 medium, 20 hard; 40 dev / 20 held-out test. Scenarios: name variants
  (initials, spelling, transliteration, order, maiden name), namesakes, partial information, no assets, several accounts, nominee vs legal heir,
  small vs large amounts, joint accounts, missing and conflicting documents, rules missing from the corpus, documents arriving in a later session,
  clean / rotated / blurry / faded documents, an injection attack in a document, and portal failures. Each appears at least 3 times. The generator
  checks itself (identity policy on every record, the real OCR on every document). See `docs/DATA_AND_RULES_GUIDE.md`.
* `python -m eval.run_eval` rebuilds every case **from its proof documents** and runs it under five variants, 3 repetitions each (different
  temperature and seed): **full Waris**, **one-pass baseline** (same tools, no identity policy, grading, Verifier or human questions), **no Verifier**,
  **no grading / re-query**, and **Waris with the LLM off**. `python -m eval.analyze results/main` writes tables, plots and a failure analysis;
  `python -m eval.judge` validates an LLM judge for letters and scores every letter.
* The family is simulated by a scripted oracle that answers from the answer key (disclosed in every result). Where OCR cannot read a field
  (a blurry certificate) the harness types the true value, as a family would on the confirm screen; those are counted as `manual_fields`.

### Headline results (held-out 20 test families, 3 repetitions; full tables in `results/main/summary.md`)
| | One-pass baseline | Waris − grading | Waris − Verifier | Waris, LLM off | **Full Waris** |
|---|---|---|---|---|---|
| Status accuracy | 73.1 % | 92.3 % | 100 % | 100 % | **100 %** |
| Checklist F1 | 61.7 % | 69.0 % | 97.1 % | 100 % | **100 %** |
| Cases fully correct | 25.0 % | 35.0 % | 70.0 % | 100 % | **100 %** |
| Wrong-person claims | 3 | 0 | 0 | 0 | **0** |
| Family questions asked when needed | 0.0 % | 100 % | 100 % | 100 % | **100 %** |

* Over all 60 families the baseline claims a stranger's money **8 times**; full Waris 0.
* **OCR rebuilt the case exactly** for 60 of 60 families (field accuracy 100.0 %); 10 fields in total
  had to be typed because a document was unreadable on purpose.
* **Fresh draw:** `data/cases_unseen` (new seed, generated after the decision code was frozen): full Waris status accuracy 100 %;
  baseline 71.0 % with 15 wrong-person claims.
* **Verifier stress set** (`data/cases_stress`: the family holds everything except the name affidavit): status accuracy without the Verifier
  0.0 % vs 100 % with it.
* **LLM off = same accuracy.** The accuracy comes from the loops and fixed code; the LLM adds flexible tool choice and letter wording (about 4 calls a case).
* **Letters:** deterministic reference checker 4.76 / 5 for full Waris vs 3.76 for the baseline;
  the LLM judge is validated against that checker (89 % agreement, κ 0.56).

## Run it (Windows, PowerShell or Git Bash)
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
ollama pull llama3.1:8b ; ollama pull nomic-embed-text      # optional: without them Waris uses deterministic fallbacks
.venv\Scripts\python -m data.generate_cases                  # 60 families + proofs + portals (already committed; reproducible)
.\run_ui.bat                                                  # the UI (http://localhost:8501)
.venv\Scripts\python -m waris.run --proofs demo_proofs\sundaram_pillai_hard --fresh --forget --answers y,y     # the same from a terminal
```
The mock portals start automatically.

| Command | Shows |
|---|---|
| `python -m waris.run --proofs demo_proofs\ramaswamy_subramanian_demo --fresh --forget` | the classic demo: name variant, rule graded unfit, family question |
| `... --proofs demo_proofs\<folder> --no-llm` | the same without the LLM (identical statuses) |
| `... --proofs demo_proofs\<folder> --later` | the folder's `later/` documents as well (a second session) |
| `... --exit-at-pause` then rerun without `--fresh` | **durable resume** from the SQLite checkpoint |
| `python -m waris.run --case meena` | developer path: a benchmark case from its structured `input.json` |
| `python -m waris.run --show-graph` | the graph as Mermaid |
| `python -m pytest -q` | the tests (`WARIS_TEST_ALL=1` runs all 60 families end to end) |
| `python scripts/ui_check.py` | a real-browser walkthrough of the upload flow (Chrome + playwright, UI running) |
| `.\scripts\reproduce.ps1 [-Quick]` | everything: generate, test, evaluate, analyse, judge |

The UI has four tabs: **File a claim** (upload, what Waris read, live agent timeline, family questions as buttons, claim packs, letters, crash-and-resume,
add more documents), **Rules & RAG explorer**, **Evaluation (60 cases)** and **Graph & trace**. Traces are written to `traces/` and, with
`docker compose up -d`, to Langfuse at http://localhost:3001 (login `waris@example.com` / `waris-demo-pass`; keys pre-seeded in `.env.example`).

## Layout
```
waris/            state graph run config guardrails tracing memory llm doc_codes baseline intake
  agents/         supervisor doc_intake tracer rules_expert builder verifier finalize letters human
  tools/          portals name_match retrieval status ocr
portals/app.py    mock bank / insurer / registry (FastAPI + SQLite): ONE shared database, injectable faults
demo_proofs/      one folder per family: the documents to upload + fields.json + README.txt (+ later/)
data/             generate_cases.py scans.py rules/*.md (11 cited rules) cases/{meena, e01..h20}/ portals.db split.json index.json
                  cases_unseen/ (fresh seed)  cases_stress/ (Verifier stress)
eval/             metrics run_eval analyze judge
results/          main/ unseen/ stress/ (runs, summary, figures, failures, letters)  judge/ (validation)
tests/            core, benchmark (all 60 families from their documents), UI
app/              Streamlit UI
docs/             explainer, guides, speaker scripts, Review-2 deck and design document
```

## Limits (every loop is bounded)
Verifier rounds ≤ 6 · RAG re-queries ≤ 2 per asset · Tracer steps ≤ 8 · LLM calls ≤ 40 per case · tool timeout 10 s, 2 retries.
Hitting a limit makes the asset `NEEDS_HUMAN_REVIEW`; the same Verifier failure twice escalates it.

## Honest scope
* All data is synthetic and the portals are mocks; no real institution is connected and none was contacted. The documents are drawn by our own generator
  in a clean printed layout; OCR on real phone photos of real certificates is untested (that is what the confirm screen is for).
* The 11 rules follow public RBI / IRDAI / IEPF procedure types but are marked `verified: illustrative` (the Rs 5 lakh small/large split is illustrative).
  Waris gives no legal advice.
* The benchmark was written by the team for this system, so near-perfect scores on it show the machinery works end to end, not that it generalises to real
  portals. The baseline and the ablations show what each agentic component contributes on the same families.
* The LLM judge is checked against a deterministic reference checker and a template for the team's own marks (`results/judge/human_marks_template.csv`).
