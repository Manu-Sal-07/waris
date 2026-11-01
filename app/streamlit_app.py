"""Waris demo UI.   streamlit run app/streamlit_app.py

Tabs: Run a case (live agent timeline, scans + OCR, family questions as buttons, claim packs, letters, scorecard)
      Rules & RAG explorer (the rule corpus, retrieval, and fit grading made visible)
      Evaluation (60-case results: baseline vs Waris vs ablations, judge validation, failures)
      Graph & trace (architecture, graph, full trace table)
"""
import atexit
import html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from langgraph.types import Command

from eval.metrics import score_case
from waris import config, llm, memory
from waris.doc_codes import DOC_CODES
from waris.graph import build_graph, clear_thread, open_checkpointer
from waris.run import start_portals
from waris.tools import portals as portal_tools
from waris.tools import retrieval
from waris.tracing import TRACE

st.set_page_config(page_title="Waris", page_icon="W", layout="wide")
NODES = ["intake_validate", "supervisor_plan", "doc_intake", "tracer", "identity_gate", "human_confirm", "rules_expert",
         "builder", "verifier", "finalize", "draft_letters", "final_approval"]
AGENT_COLOR = {"supervisor": "#8e5ea2", "tracer": "#0e8a9a", "rules_expert": "#c98a00", "builder": "#2e8b57",
               "verifier": "#c0392b", "human": "#1f4e9c", "guard": "#a93226", "system": "#777", "memory": "#7d3c98",
               "llm": "#555"}
STATUS_STYLE = {"READY": ("#2e8b57", "READY"), "MISSING_ITEMS": ("#c98a00", "MISSING ITEMS"),
                "NEEDS_HUMAN_REVIEW": ("#c0392b", "NEEDS HUMAN REVIEW")}

st.markdown("""<style>
.chip{display:inline-block;color:#fff;border-radius:10px;padding:1px 8px;font-size:12px;margin-right:6px}
.node{display:inline-block;border:1.5px solid #b8c4cc;border-radius:8px;padding:2px 8px;margin:2px;font-size:12px;color:#6b7885}
.node.done{background:#dcefef;border-color:#0b6e6e;color:#0b6e6e;font-weight:600}
.node.now{background:#fbefd9;border-color:#e8a33d;color:#8a5a00;font-weight:700}
.ev{padding:4px 0;border-bottom:1px solid #eef1f3;font-size:13.5px;line-height:1.35}
.ev .k{font-weight:700;margin-right:6px;font-size:12px;color:#444}
.warnmsg{color:#a93226}
.badge{color:#fff;border-radius:6px;padding:3px 10px;font-weight:700;font-size:13px}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- shared resources
@st.cache_resource
def _portals():
    proc = start_portals()
    if proc:
        atexit.register(proc.terminate)
    return True


@st.cache_resource
def _index():
    retrieval.index_rules()
    return retrieval.backend()


_portals()
EMBED = _index()
ss = st.session_state
ss.setdefault("run", None)


def langfuse_up() -> bool:
    try:
        import httpx
        return httpx.get(os.getenv("LANGFUSE_HOST", "http://localhost:3001") + "/api/public/health", timeout=1).status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------- rendering helpers
def render_events(ph) -> None:
    rows = []
    for e in reversed(TRACE.events):                      # newest first, so the live view always shows the latest step
        if e["kind"] == "NODE":
            continue
        col = AGENT_COLOR.get(e["agent"], "#555")
        warn = e["level"] == "warn" or any(w in e["message"] for w in ("UNFIT", "FAIL", "REJECTED", "ABSTAIN"))
        rows.append(f"<div class='ev'><span class='chip' style='background:{col}'>{e['agent']}</span>"
                    f"<span class='k'>{e['kind']}</span><span class='{'warnmsg' if warn else ''}'>{html.escape(e['message'])}</span></div>")
    ph.markdown("".join(rows) or "<i>No events yet. Press <b>Start case</b>.</i>", unsafe_allow_html=True)


def render_stepper(ph, run) -> None:
    visited = set(run["visited"]) if run else set()
    nxt = set(run["next"]) if run else set()
    chips = "".join(f"<span class='node {'now' if n in nxt else 'done' if n in visited else ''}'>{n}</span>" +
                    ("&rarr;" if i < len(NODES) - 1 else "") for i, n in enumerate(NODES))
    ph.markdown(chips, unsafe_allow_html=True)


def drive(inp, ph_events, ph_steps) -> None:
    run = ss.run
    run["pending"] = None
    for chunk in run["graph"].stream(inp, run["cfg"], stream_mode="updates"):
        if "__interrupt__" in chunk:
            run["pending"] = chunk["__interrupt__"][0].value
        else:
            run["visited"] += [k for k in chunk if k not in run["visited"]]
        snap = run["graph"].get_state(run["cfg"])
        run["next"] = list(snap.next)
        render_events(ph_events)
        render_stepper(ph_steps, run)
    snap = run["graph"].get_state(run["cfg"])
    run["next"] = list(snap.next)
    if run["pending"] is None:
        run["state"], run["finished"] = snap.values, True
    TRACE.finish()


def start_case(case_name: str, use_llm: bool, fresh_memory: bool, session2: bool = False) -> dict:
    case = json.loads((config.CASES_DIR / case_name / "input.json").read_text(encoding="utf-8"))
    if session2:
        case = {**case, "scans": case.get("scans", []) + case.get("session2_scans", [])}
    portal_tools.set_case(case["case_id"] if (config.CASES_DIR / case_name / "portals.db").exists() else None)
    saver = open_checkpointer()
    graph = build_graph(saver)
    clear_thread(saver, case["case_id"])
    if fresh_memory and not session2:
        memory.forget(case["case_id"])
    llm.set_enabled(use_llm)
    if use_llm and not llm.warm_up():
        st.toast("Ollama model unavailable: using deterministic fallbacks", icon="⚠️")
    TRACE.configure(case["case_id"], echo=False, append=False)
    return {"graph": graph, "cfg": {"configurable": {"thread_id": case["case_id"]}}, "case": case, "case_name": case_name,
            "pending": None, "finished": False, "state": None, "visited": [], "next": [], "restarted": False}


def simulate_restart() -> None:
    """Throw away every in-memory object and rebuild from the SQLite checkpoint (a killed-and-restarted process)."""
    run = ss.run
    TRACE.finish()
    saver = open_checkpointer()
    graph = build_graph(saver)
    snap = graph.get_state(run["cfg"])
    TRACE.configure(run["case"]["case_id"], echo=False, append=True)
    run.update(graph=graph, next=list(snap.next), restarted=True)
    run["pending"] = snap.tasks[0].interrupts[0].value if snap.tasks and snap.tasks[0].interrupts else None


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## Waris")
    st.caption("Agentic AI for unclaimed inheritance recovery. **Advisory only**: never files a claim, never decides heirship. All data is synthetic.")
    cases = sorted(p.name for p in config.CASES_DIR.iterdir() if (p / "input.json").exists())
    _idx = {c["case_id"]: c for c in json.loads((config.CASES_DIR / "index.json").read_text(encoding="utf-8"))} \
        if (config.CASES_DIR / "index.json").exists() else {}
    case_name = st.selectbox("Case", cases, format_func=lambda c: f"{c}  ·  {_idx[c]['difficulty']}" if c in _idx else f"{c}  ·  hand-built demo")
    if case_name in _idx:
        st.caption("Tests: " + ", ".join(_idx[case_name]["tags"]))
    use_llm = st.checkbox(f"Use local LLM ({config.OLLAMA_MODEL})", value=True,
                          help="The LLM only chooses which portal to search next. Off = fixed fallback order (still a full run).")
    fresh_mem = st.checkbox("Forget the family's earlier answers", value=True,
                            help="Untick and run twice to see long-term memory skip the identity question.")
    start = st.button("▶  Start case", type="primary", width="stretch")
    st.divider()
    st.markdown(f"**Embeddings:** `{EMBED}`  \n**Langfuse:** {'on, [open](http://localhost:3001)' if langfuse_up() else 'off (local trace only)'}")
    st.markdown("**Limits:** rounds ≤ 6 · re-queries ≤ 2 · LLM calls ≤ 40 · timeout 10 s")

tab_run, tab_rag, tab_eval, tab_graph = st.tabs(["Run a case", "Rules & RAG explorer", "Evaluation (60 cases)", "Graph & trace"])

# ================================================================ TAB 1: run
with tab_run:
    run = ss.run
    st.markdown("##### Pipeline")
    steps_ph = st.empty()
    left, right = st.columns([1, 1], gap="large")
    with right:
        st.markdown("##### Agent timeline (live, newest first)")
        ev_ph = st.container(height=620).empty()
    with left:
        q_box = st.container()

    # ---- family question (buttons rendered BEFORE actions so a click is seen on the next rerun)
    answer = None
    if run and run["pending"]:
        p = run["pending"]
        with q_box:
            if p["kind"] == "confirm_identity":
                st.warning("**Waris needs the family.**  A medium match is never accepted automatically.")
                st.write(p["question"])
                c1, c2 = st.columns(2)
                if c1.button("✔  Yes, that is him", width="stretch", key="yes"):
                    answer = "y"
                if c2.button("✘  No, different person", width="stretch", key="no"):
                    answer = "n"
            else:
                st.warning("**Final approval.**  " + p["question"])
                st.json(p.get("summary", {}))
                c1, c2 = st.columns(2)
                if c1.button("✔  Approve release", width="stretch", key="yes"):
                    answer = "y"
                if c2.button("✘  Decline", width="stretch", key="no"):
                    answer = "n"
            if st.button("⚡ Simulate crash & restart (resume from checkpoint)", key="crash"):
                simulate_restart()
                st.rerun()

    # ---- actions
    if start or ss.pop("go_session2", False):
        is_s2 = not start
        ss.run = run = start_case(case_name if start else ss.run["case_name"], use_llm, fresh_mem, session2=is_s2)
        with st.spinner("Running agents..."):
            drive({"case_id": run["case"]["case_id"], "deceased": run["case"]["deceased"],
                   "claimant": run["case"]["claimant"], "scans": run["case"].get("scans", [])}, ev_ph, steps_ph)
        st.rerun()
    elif answer and run:
        with st.spinner("Resuming..."):
            drive(Command(resume=answer), ev_ph, steps_ph)
        st.rerun()

    # ---- static render
    render_stepper(steps_ph, run)
    render_events(ev_ph)
    with left:
        if run and run.get("restarted") and not run["finished"]:
            st.info("Process restarted: all in-memory objects were discarded and the graph was rebuilt from the SQLite checkpoint. "
                    f"It resumes at **{', '.join(run['next'])}**.")
        if not run:
            st.info("Pick a case in the sidebar and press **Start case**. Watch for the three moments: "
                    "name variant & namesakes → rule graded unfit → family confirmation.")
        if run and run["finished"]:
            state = run["state"]
            st.success(f"Done in {state.get('round', 0)} Verifier round(s), {state.get('llm_calls', 0)}/{config.MAX_LLM_CALLS} LLM calls. "
                       f"Released to family: **{'yes' if state.get('released') else 'no'}**")
            if state.get("scan_results"):
                st.markdown("##### Scanned documents (OCR)")
                cols = st.columns(min(3, len(state["scan_results"])))
                for i, sr in enumerate(state["scan_results"]):
                    img = config.CASES_DIR / run["case_name"] / "scans" / sr["file"]
                    with cols[i % len(cols)]:
                        if img.exists():
                            st.image(str(img), width="stretch")
                        st.caption(f"{sr['file']}: " + (f"read as {sr['doc_code']} (conf {sr['confidence']})" if sr["readable"]
                                                       else f"unreadable ({sr['reason']}), not counted"))
            for c in state.get("doc_conflicts", []):
                st.error(f"Documents disagree: {c['scan']} shows {c['field']} {c['scan_value']} but the family said {c['family_value']}. "
                         "Waris does not pick one: a human decides.")
            if not state["claim_packs"]:
                st.info("**Nothing found.** No asset of this person was found in any searched source. Waris does not invent assets.")
            for e in state.get("tool_errors", []):
                st.warning(f"{e['tool']} was unavailable ({e['error'][:60]}). Retry later or ask the institution directly.")
            st.markdown("##### Claim packs")
            for aid, pack in state["claim_packs"].items():
                color, label = STATUS_STYLE[pack["status"]]
                st.markdown(f"**{aid}** &nbsp; <span class='badge' style='background:{color}'>{label}</span>", unsafe_allow_html=True)
                if pack["requirements"]:
                    st.dataframe(pd.DataFrame([{"document": r["doc_code"], "cited rule": r["rule_id"], "family has it": "✔" if r["have_it"] else "✘ missing"}
                                               for r in pack["requirements"]]), hide_index=True, width="stretch")
                for n in pack["notes"]:
                    if n.startswith(("abstained", "escalated", "stopped")):
                        st.error(n)
            if state.get("letters"):
                st.markdown("##### Claim letters (drafts for the family to review)")
                for aid, text in state["letters"].items():
                    with st.expander(f"Letter for {aid}"):
                        st.code(text, language=None)
            if (config.CASES_DIR / run["case_name"] / "input.json").exists() and \
                    json.loads((config.CASES_DIR / run["case_name"] / "input.json").read_text(encoding="utf-8")).get("session2_scans") \
                    and not run.get("session2"):
                st.info("This case continues in a later session: the family sends more documents. Memory keeps their earlier answers.")
                if st.button("▶ Run session 2 (new documents arrive)", key="s2"):
                    ss.go_session2 = True
                    st.rerun()
            if state.get("rejected_candidates"):
                with st.expander(f"Not claimed ({len(state['rejected_candidates'])} records rejected)"):
                    for r in state["rejected_candidates"]:
                        st.write(f"`{r['asset_id']}` {r['holder_name']}: {r['reason']} (score {r['score']})")
            key = config.CASES_DIR / run["case_name"] / "answer_key.json"
            if key.exists():
                s = score_case(state["claim_packs"], json.loads(key.read_text(encoding="utf-8")), retrieval.rule_exists)
                st.markdown("##### Scorecard vs answer key")
                m = st.columns(3)
                m[0].metric("Asset recall", f"{s['asset_recall']:.0%}")
                m[1].metric("Wrong-person matches", s["wrong_person_matches"], help="target 0")
                m[2].metric("Status accuracy", f"{s['status_accuracy']:.0%}")
                m = st.columns(3)
                m[0].metric("Checklist P / R", f"{s['checklist_precision']:.0%} / {s['checklist_recall']:.0%}")
                m[1].metric("Citation coverage", f"{s['citation_coverage']:.0%}")
                m[2].metric("Abstention correct", "yes" if s["abstention_correct"] else "no")
                st.caption("One case: it shows the harness works. The 60-case evidence is in the Evaluation tab.")

# ================================================================ TAB 2: RAG
with tab_rag:
    st.markdown("### Where the rules and the RAG live")
    st.markdown(
        f"- **Rule corpus:** `data/rules/*.md` ({len(retrieval.load_rules())} cited, versioned files; front matter = metadata used for grading)\n"
        "- **Index:** `waris/tools/retrieval.py` builds a persistent **Chroma** collection (`.cache/chroma`); "
        f"embeddings backend now: **`{EMBED}`** (`nomic-embed-text` via Ollama, offline hash fallback)\n"
        "- **Agentic loop:** `waris/agents/rules_expert.py` = query → retrieve → **grade** → re-query (≤ 2, excluding rejected rules) → **abstain**\n"
        "- **Citations:** every checklist item carries a `rule_id`; the Verifier rejects uncited or unbacked items")
    rules = retrieval.load_rules()
    st.markdown("##### 1. The corpus")
    st.dataframe(pd.DataFrame([{"rule_id": r["rule_id"], "institution": r["institution_type"], "topic": r["topic"],
                                "applies_to": r["applies_to"], "requires": ", ".join(r["requires"]),
                                "verified": r["verified"], "v": r["version"]} for r in rules]), hide_index=True, width="stretch")
    pick = st.selectbox("Open a rule", [r["rule_id"] for r in rules])
    r = retrieval.rules_by_id()[pick]
    c1, c2 = st.columns([2, 1])
    c1.markdown(f"**{r['title']}**\n\n{r['text']}")
    c2.json({k: v for k, v in r.items() if k not in ("text", "file", "title")})
    st.info("Deliberate gaps: **no insurer rule when the policy's nominee has died**, and **no registry rule for joint holders**. "
            "Try them below: Waris must say \"I don't know\".")

    st.markdown("##### 2. Try retrieval + grading yourself")
    a, b, c = st.columns(3)
    inst = a.selectbox("Institution", ["bank", "registry", "insurer"])
    topic = b.selectbox("Need", ["claim_procedure", "name_variation"])
    ctype = c.selectbox("Claimant is a", ["legal_heir", "nominee", "joint_holder"])
    nom = a.selectbox("Nominee status", ["no nominee / unknown", "alive", "deceased"])
    band = c.selectbox("Amount", ["any", "small (up to 5 lakh)", "large (above 5 lakh)"]).split(" ")[0]
    k = b.slider("Top-k", 1, 3, 3)
    default_q = {"claim_procedure": f"{inst} claim procedure: documents required to claim the deposit of a deceased account holder",
                 "name_variation": f"{inst} name variation between records: initials or spelling difference, affidavit proof required"}[topic]
    q = st.text_area("Query", default_q, height=70)
    if st.button("Retrieve and grade", type="primary"):
        facts = {"institution_type": inst, "topic": topic, "claimant_type": ctype, "amount_band": band,
                 "nominee_alive": {"alive": True, "deceased": False}.get(nom),
                 "nominee_status": nom if nom in ("alive", "deceased") else None}
        got = retrieval.retrieve_rules(q, inst, topic, k=k)
        if not got:
            st.error("Nothing retrieved for this institution/topic.")
        rows = []
        for i, rule in enumerate(got):
            g = retrieval.grade_rule(facts, rule)
            rows.append({"rank": i + 1, "rule_id": rule["rule_id"], "distance": rule["distance"],
                         "similarity": max(0.0, 1 - rule["distance"]), "applies_to": rule["applies_to"],
                         "verdict": "FITS" if g["fits"] else "UNFIT", "why": g["reason"]})
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                         column_config={"similarity": st.column_config.ProgressColumn("similarity", min_value=0, max_value=1)})
            top = rows[0]
            if top["verdict"] == "UNFIT":
                fits = [x for x in rows if x["verdict"] == "FITS"]
                st.warning(f"The **most similar** rule (`{top['rule_id']}`) is **UNFIT**: {top['why']}. "
                           + (f"Corrective RAG would exclude it and re-query, finding `{fits[0]['rule_id']}`." if fits
                              else "No other rule fits, so the agent **abstains** (\"I don't know\") and asks a human."))
            else:
                st.success(f"Top rule `{top['rule_id']}` fits: {top['why']}")

# ================================================================ TAB 3: evaluation
with tab_eval:
    res = ROOT / "results" / "main"
    st.markdown("### Evaluation on the 60 synthetic cases")
    if not (res / "summary.md").exists():
        st.info("No results yet. Run: `python -m eval.run_eval --out results/main` then `python -m eval.analyze results/main`.")
    else:
        st.caption("Labels come from the generator, never from an LLM. The family is simulated by a scripted oracle that answers "
                   "from the answer key. Headline numbers use the 20 held-out test cases; the 40 dev cases are reported separately.")
        st.markdown((res / "summary.md").read_text(encoding="utf-8"))
        figs = res / "figures"
        c1, c2 = st.columns(2)
        for i, name in enumerate(["quality_test.png", "wrong_person_test.png", "cost_test.png", "difficulty_all.png"]):
            if (figs / name).exists():
                (c1 if i % 2 == 0 else c2).image(str(figs / name), width="stretch")
        if (res / "failures.md").exists():
            with st.expander("Failure analysis (every imperfect run of full Waris)"):
                st.markdown((res / "failures.md").read_text(encoding="utf-8"))
        jv = ROOT / "results" / "judge" / "validation.json"
        if jv.exists():
            st.markdown("##### LLM-as-judge validation")
            st.json(json.loads(jv.read_text(encoding="utf-8")))
        if (res / "judge_summary.json").exists():
            st.markdown("##### Letter quality (judge model, 5 criteria per letter)")
            st.dataframe(pd.DataFrame(json.loads((res / "judge_summary.json").read_text(encoding="utf-8"))).T, width="stretch")

# ================================================================ TAB 4: graph & trace
with tab_graph:
    st.markdown("### Architecture and agent graph")
    fig = ROOT / "docs" / "figures"
    if (fig / "fig1_architecture.png").exists():
        st.image(str(fig / "fig1_architecture.png"), caption="Figure 1: layered architecture")
        st.image(str(fig / "fig2_graph.png"), caption="Figure 2: the LangGraph graph (dashed red = Verifier send-back, blue = human interrupts)")
    st.markdown("### Trace of the current run")
    evs = [e for e in TRACE.events if e["kind"] != "NODE"]
    if evs:
        st.dataframe(pd.DataFrame([{"t (s)": e["t"], "agent": e["agent"], "event": e["kind"], "detail": e["message"]} for e in evs]),
                     hide_index=True, width="stretch", height=420)
        st.caption(f"Saved to `traces/{TRACE.case_id}.html` and `.jsonl` on every pause and at the end. Personal data is masked.")
    else:
        st.info("Run a case first.")
