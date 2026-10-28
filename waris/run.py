"""CLI entry point:  python -m waris.run --case meena

Runs a case through the LangGraph graph, prints the agent trace live, handles human pauses
(interrupt/resume), writes traces/<case>.{jsonl,html}, and scores the result against the answer key.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import httpx
from langgraph.types import Command

from . import config, llm, memory
from .graph import build_graph, clear_thread, open_checkpointer
from .tools import retrieval
from .tracing import TRACE

BOLD, DIM, RESET = "\033[1m", "\033[90m", "\033[0m"


def _portal_up() -> bool:
    try:
        return httpx.get(config.PORTAL_URL + "/health", timeout=1).status_code == 200
    except Exception:
        return False


def start_portals():
    """Start the mock portals if they are not already running. Returns the process (or None)."""
    if _portal_up():
        return None
    from data.seed_portals import seed
    if not config.PORTAL_DB.exists():
        seed(config.PORTAL_DB)
    port = config.PORTAL_URL.rsplit(":", 1)[1]
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "portals.app:app", "--port", port, "--log-level", "error"],
                            cwd=str(config.ROOT))
    for _ in range(40):
        if _portal_up():
            return proc
        time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("mock portals did not start")


def ask_human(payload: dict, scripted: list[str]) -> str:
    print(f"\n{BOLD}>>> WAITING FOR THE FAMILY <<<{RESET}\n{payload['question']}")
    if scripted:
        ans = scripted.pop(0)
        print(f"(scripted answer: {ans})\n")
        return ans
    try:
        return input("Your answer (y/n): ").strip()
    except EOFError:
        print("\nNo keyboard input available. Run in a normal terminal, or pass --answers y,y (state is checkpointed).")
        raise SystemExit(2)


def drive(graph, config_, first_input, scripted: list[str], exit_at_pause: bool) -> dict:
    inp = first_input
    while True:
        pending = None
        for chunk in graph.stream(inp, config_, stream_mode="updates"):
            if "__interrupt__" in chunk:
                pending = chunk["__interrupt__"][0].value
        if pending is None:
            return graph.get_state(config_).values
        if exit_at_pause:
            TRACE.finish()
            print(f"\n{BOLD}Process stopped while waiting for the family. State is checkpointed.{RESET}\n"
                  "Run the same command again (without --fresh) to resume from this exact step.")
            raise SystemExit(75)
        inp = Command(resume=ask_human(pending, scripted))


def print_scorecard(state: dict, case_dir) -> None:
    from eval.metrics import score_case
    key_path = case_dir / "answer_key.json"
    if not key_path.exists():
        return
    s = score_case(state["claim_packs"], json.loads(key_path.read_text(encoding="utf-8")), retrieval.rule_exists)
    print(f"\n{BOLD}SCORECARD vs answer key{RESET} {DIM}(labels come from the generator, never from an LLM){RESET}")
    print(f"  asset recall         {s['asset_recall']:.0%}")
    print(f"  wrong-person matches {s['wrong_person_matches']}   (target 0)")
    print(f"  status accuracy      {s['status_accuracy']:.0%}")
    print(f"  checklist P / R      {s['checklist_precision']:.0%} / {s['checklist_recall']:.0%}")
    print(f"  citation coverage    {s['citation_coverage']:.0%}   (target 100%)")
    print(f"  abstention correct   {s['abstention_correct']}")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    os.system("")                                  # enable ANSI colours in older Windows consoles
    ap = argparse.ArgumentParser(description="Waris: unclaimed-inheritance claim-readiness agent (synthetic data)")
    ap.add_argument("--case", default="meena")
    ap.add_argument("--fresh", action="store_true", help="discard the checkpoint for this case and start over")
    ap.add_argument("--forget", action="store_true", help="also erase the long-term case file (family answers)")
    ap.add_argument("--answers", default="", help="scripted human answers, e.g. 'y,y' (otherwise asks in the terminal)")
    ap.add_argument("--exit-at-pause", action="store_true", help="demo durable resume: stop the process at the first pause")
    ap.add_argument("--no-llm", action="store_true", help="deterministic fallbacks only")
    ap.add_argument("--show-graph", action="store_true", help="print the graph as Mermaid and exit")
    args = ap.parse_args(argv)

    if args.no_llm:
        llm.disable()
    saver = open_checkpointer()
    graph = build_graph(saver)
    if args.show_graph:
        print(graph.get_graph().draw_mermaid())
        return 0

    case_dir = config.CASES_DIR / args.case
    case = json.loads((case_dir / "input.json").read_text(encoding="utf-8"))
    cfg = {"configurable": {"thread_id": case["case_id"]}}
    if args.fresh or args.forget:
        clear_thread(saver, case["case_id"])
    if args.forget:
        memory.forget(case["case_id"])

    resuming = bool(graph.get_state(cfg).next)
    TRACE.configure(case["case_id"], append=resuming)
    retrieval.index_rules()
    if llm.enabled() and not llm.warm_up():
        print(f"{DIM}note: Ollama model '{config.OLLAMA_MODEL}' unavailable; running with deterministic fallbacks{RESET}")
    portal_proc = start_portals()
    try:
        snap = graph.get_state(cfg)
        print(f"\n{BOLD}WARIS{RESET} {DIM}advisory only: never files a claim, never decides heirship; synthetic data{RESET}")
        print(f"{DIM}model: {config.OLLAMA_MODEL if llm.enabled() else 'none (deterministic fallbacks)'} | "
              f"limits: rounds {config.MAX_ROUNDS}, re-queries {config.MAX_REQUERY}, "
              f"LLM calls {config.MAX_LLM_CALLS} | Langfuse: {'on' if TRACE.langfuse_on else 'off (local trace)'}{RESET}\n")
        scripted = [a.strip() for a in args.answers.split(",") if a.strip()]
        if snap.next:
            print(f"{BOLD}RESUMING{RESET} case '{case['case_id']}' from checkpoint (next step: {', '.join(snap.next)})\n")
            state = drive(graph, cfg, None, scripted, args.exit_at_pause)
        elif snap.values.get("done"):
            print(f"Case '{case['case_id']}' already finished. Use --fresh to run it again.")
            state = snap.values
        else:
            state = drive(graph, cfg, {"case_id": case["case_id"], "deceased": case["deceased"],
                                       "claimant": case["claimant"], "scans": case.get("scans", [])},
                          scripted, args.exit_at_pause)
        print(f"\n{BOLD}FINAL CLAIM PACKS{RESET}  (rounds used: {state.get('round', 0)}, "
              f"LLM calls: {state.get('llm_calls', 0)}/{config.MAX_LLM_CALLS})")
        for aid, p in state["claim_packs"].items():
            print(f"  {aid:<22} {p['status']:<20} missing: {', '.join(p['missing']) or '-'}")
        print_scorecard(state, case_dir)
        out = TRACE.finish()
        print(f"\ntrace: {out['html']}" + ("   (also sent to Langfuse)" if out["langfuse"] else ""))
        return 0
    finally:
        if portal_proc:
            portal_proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
