"""Batch evaluation harness.

    python -m eval.run_eval --variants full,baseline,no_verifier,no_grading,full_nollm --split all --repeats 3 --out results/main

Runs every selected case under every variant, `repeats` times (rep 0: temperature 0; later reps: higher temperature
and a different seed), scores each run against the generator's answer key and appends one JSON line per run to
<out>/runs.jsonl (resumable: finished runs are skipped).  Then use `python -m eval.analyze <out>` for tables and plots.

Every run starts from the family's PROOF DOCUMENTS (the png files of the case's proof folder): Waris reads them with OCR,
builds the case, and only then does the agent pipeline start. Fields OCR cannot read (a blurry death certificate) fall back to
what the family would type; those are counted as `manual_fields`. The family is simulated by a scripted oracle that answers "yes" exactly when the record being asked about is a real
asset of the deceased (from the answer key) and "no" otherwise. This is disclosed in every result; it lets the
human-in-the-loop path run unattended without ever giving the agent the key.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from waris import baseline, config, intake, llm, memory
from waris.graph import build_graph
from waris.tools import portals, retrieval
from waris.tracing import TRACE
from eval.metrics import score_case

VARIANTS = {
    "full": {"ablate": set(), "llm": True, "desc": "full Waris"},
    "full_nollm": {"ablate": set(), "llm": False, "desc": "full Waris, LLM switched off (fixed fallbacks)"},
    "baseline": {"ablate": set(), "llm": True, "desc": "one-pass baseline (no identity policy, grading, Verifier, HITL)"},
    "no_verifier": {"ablate": {"no_verifier"}, "llm": True, "desc": "Waris without the Verifier"},
    "no_grading": {"ablate": {"no_grading"}, "llm": True, "desc": "Waris without rule grading / re-query"},
}
REP_TEMPS = [(0.0, 0), (0.3, 1), (0.7, 2)]
RESULTS_ROOT = config.ROOT / "results"


def case_ids(split: str) -> list[str]:
    sp = json.loads((config.CASES_DIR / "split.json").read_text(encoding="utf-8"))
    if split == "dev":
        return sp["dev"]
    if split == "test":
        return sp["test"]
    return sorted(sp["dev"] + sp["test"])


def load_case(cid: str) -> tuple[dict, dict]:
    d = config.CASES_DIR / cid
    return (json.loads((d / "input.json").read_text(encoding="utf-8")),
            json.loads((d / "answer_key.json").read_text(encoding="utf-8")))


def _drive(graph, cfg, first_input, truth_ids: set[str]) -> tuple[dict, list[str]]:
    """Run to completion, answering human pauses with the scripted family oracle."""
    asked, inp = [], first_input
    while True:
        pending = None
        for chunk in graph.stream(inp, cfg, stream_mode="updates"):
            if "__interrupt__" in chunk:
                pending = chunk["__interrupt__"][0].value
        if pending is None:
            return graph.get_state(cfg).values, asked
        if pending["kind"] == "confirm_identity":
            rid = pending["asset_id"].split(":", 1)[1]
            asked.append(rid)
            inp = Command(resume="y" if rid in truth_ids else "n")
        else:
            inp = Command(resume="y")


def proofs_root() -> Path:
    return config.ROOT / "demo_proofs" if config.CASES_DIR.resolve() == (config.ROOT / "data" / "cases").resolve() else config.CASES_DIR / "proofs"


def _truth_facts(case: dict) -> dict:
    d, c = case["deceased"], case["claimant"]
    return {"deceased_name": d["name"], "deceased_dob": d["dob"], "deceased_dod": d["dod"], "deceased_city": d["city"],
            "claimant_name": c["name"], "relationship": c["relationship"]}


def _extraction(built_case: dict, truth: dict, sources: dict) -> dict:
    """How faithfully did OCR rebuild the case the generator started from?"""
    bd, bc, td, tc = built_case["deceased"], built_case["claimant"], truth["deceased"], truth["claimant"]
    checks = {"deceased_name": bd["name"] == td["name"], "dob": bd["dob"] == td["dob"], "dod": bd["dod"] == td["dod"],
              "city": bd["city"] == td["city"], "other_names": sorted(bd["aliases"]) == sorted(td["aliases"]),
              "claimant_name": bc["name"] == tc["name"], "relationship": bc["relationship"] == tc["relationship"]}
    typed = sum(1 for v in sources.values() if v.startswith("typed"))
    return {"ex_n": len(checks), "ex_ok": sum(checks.values()), "manual_fields": typed,
            "ex_failed": [k for k, v in checks.items() if not v]}


def _waris_session(case: dict, truth_ids: set[str], thread: str) -> tuple[dict, list[str]]:
    graph = build_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 80}
    return _drive(graph, cfg, {"case_id": case["case_id"], "deceased": case["deceased"], "claimant": case["claimant"],
                               "scans": case.get("scans", []), "claim_for": case.get("claim_for", intake.CLAIM_FOR)}, truth_ids)


def run_one(cid: str, variant: str, rep: int, out: Path, save_letters: bool, mode: str = "documents") -> dict:
    """mode 'documents': rebuild the case from the proof files by OCR (the product path).  'structured': use input.json directly."""
    spec = VARIANTS[variant]
    truth, key = load_case(cid)
    truth_ids = {a["record_id"] for a in key["assets"]}
    temp, seed = REP_TEMPS[rep % len(REP_TEMPS)]
    config.LLM_TEMPERATURE, config.LLM_SEED, config.ABLATE = temp, seed, set(spec["ablate"])
    llm.set_enabled(bool(spec["llm"]))
    run_id = f"{cid}__{variant}__r{rep}"
    ex = {}
    if mode == "documents":
        folder = proofs_root() / key["proof_folder"]
        built = intake.build_case(intake.list_proofs(folder), key["form"], fallback=_truth_facts(truth))
        case = built["case"]
        ex = _extraction(case, truth, built["sources"])
        later = [str(folder / f) for f in key.get("later_files", [])]
    else:
        case = {**truth, "claim_for": intake.CLAIM_FOR}
        later = []
    memory.forget(case["case_id"])
    TRACE.configure(run_id, out_dir=out / "traces", echo=False, langfuse=False)
    t0, asked, reasked = time.time(), [], 0
    if variant == "baseline":
        state = baseline.run_baseline(case)
        if later:
            state = baseline.run_baseline({**case, "scans": case["scans"] + later})
    else:
        state, asked = _waris_session(case, truth_ids, run_id)
        if later:                                       # more documents arrive in a later session; memory persists
            state, asked2 = _waris_session({**case, "scans": case["scans"] + later}, truth_ids, run_id + "-s2")
            reasked = len(set(asked2) & set(asked))
            asked = asked + asked2
    wall = round(time.time() - t0, 2)
    TRACE.finish()
    sc = score_case(state.get("claim_packs", {}), key, retrieval.rule_exists, asked=asked, state=state)
    if save_letters:
        ld = out / "letters" / variant / cid
        ld.mkdir(parents=True, exist_ok=True)
        for aid, text in state.get("letters", {}).items():
            (ld / (aid.replace(":", "_") + ".txt")).write_text(text, encoding="utf-8")
    sp = json.loads((config.CASES_DIR / "split.json").read_text(encoding="utf-8"))
    return {"run_id": run_id, "case_id": cid, "split": "test" if cid in sp["test"] else "dev", "difficulty": key["difficulty"],
            "tags": key["tags"], "variant": variant, "rep": rep, "temperature": temp, "mode": mode,
            "llm_calls": state.get("llm_calls", 0), "tool_calls": len(state.get("tools_done", [])),
            "rounds": state.get("round", 0), "requeries": sum(state.get("requery_count", {}).values()),
            "send_backs": sum(1 for f in state.get("verifier_feedback", []) if not f.get("ok", True)),
            "questions": len(asked), "reasked_in_session2": reasked, "wall_s": wall,
            "injection_flagged": any("instruction-like" in e["message"] for e in TRACE.events),
            "statuses": {a: p["status"] for a, p in state.get("claim_packs", {}).items()},
            "letters": len(state.get("letters", {})), **ex, **sc}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="full,baseline,no_verifier,no_grading,full_nollm")
    ap.add_argument("--split", default="all", choices=["dev", "test", "all"])
    ap.add_argument("--cases", default="", help="comma-separated case ids (overrides --split)")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", default="results/main")
    ap.add_argument("--no-warm", action="store_true")
    ap.add_argument("--mode", default="documents", choices=["documents", "structured"],
                    help="documents = rebuild every case from its proof files by OCR (default); structured = read input.json directly")
    ap.add_argument("--cases-dir", default="", help="evaluate a different set of generated cases, e.g. data/cases_unseen")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if not out.is_absolute():
        out = config.ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    (out / "traces").mkdir(exist_ok=True)
    if args.cases_dir:
        config.CASES_DIR = Path(args.cases_dir) if Path(args.cases_dir).is_absolute() else config.ROOT / args.cases_dir
    config.PORTAL_DB = config.CASES_DIR / "portals.db"                 # one shared portal database per dataset

    from portals.app import app
    portals.set_client(TestClient(app, base_url="http://waris-portals"))
    config.CASE_FILE_DB = out / "case_files.db"
    config.CHROMA_DIR = out / ".chroma"                 # own vector index: parallel runs must not rebuild each other's
    retrieval.index_rules()
    if not args.no_warm and not llm.warm_up():
        print("note: Ollama model unavailable; LLM variants will use fixed fallbacks")
    ids = [c for c in args.cases.split(",") if c] or case_ids(args.split)
    variants = [v for v in args.variants.split(",") if v]
    runs_file = out / "runs.jsonl"
    done = set()
    if runs_file.exists():
        done = {json.loads(l)["run_id"] for l in runs_file.read_text(encoding="utf-8").splitlines() if l.strip()}
    todo = [(cid, v, r) for r in range(args.repeats) for v in variants for cid in ids if f"{cid}__{v}__r{r}" not in done]
    print(f"{len(todo)} runs to do ({len(done)} already finished) -> {out}", flush=True)
    t_start = time.time()
    for n, (cid, v, r) in enumerate(todo, 1):
        row = run_one(cid, v, r, out, save_letters=(r == 0), mode=args.mode)
        with runs_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if n % 10 == 0 or n == len(todo):
            el = time.time() - t_start
            print(f"  {n}/{len(todo)} done, {el / 60:.1f} min elapsed, ~{el / n * (len(todo) - n) / 60:.1f} min left", flush=True)
    llm.set_enabled(True)
    print("finished ->", runs_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
