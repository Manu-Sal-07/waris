"""Waris demo UI.   streamlit run app/streamlit_app.py

The family uploads the PROOFS they hold (death certificate, their own ID, proof of relationship, any forms) and fills three
fields (which institutions, in what capacity, other names). Waris reads the documents with OCR, shows what it read, builds the
case, and runs the agents. No case is picked from a list.

Tabs: File a claim (upload, what Waris read, live agent timeline, family questions as buttons, claim packs, letters, scorecard)
      Rules & RAG explorer (the rule corpus, retrieval, and fit grading made visible)
      Evaluation (60 cases: baseline vs Waris vs ablations, judge validation, failures)
      Graph & trace (architecture, graph, full trace table)
"""
import atexit
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from langgraph.types import Command

from eval.metrics import score_case
from waris import config, intake, llm, memory
from waris.doc_codes import DOC_CODES
from waris.graph import build_graph, clear_thread, open_checkpointer
from waris.run import start_portals
from waris.tools import retrieval
from waris.tracing import TRACE

st.set_page_config(page_title="Waris", page_icon="W", layout="wide")
NODES = ["read_documents", "intake_validate", "supervisor_plan", "doc_intake", "tracer", "identity_gate", "human_confirm",
         "rules_expert", "builder", "verifier", "finalize", "draft_letters", "final_approval"]
AGENT_COLOR = {"supervisor": "#8e5ea2", "tracer": "#0e8a9a", "rules_expert": "#c98a00", "builder": "#2e8b57",
               "verifier": "#c0392b", "human": "#1f4e9c", "guard": "#a93226", "system": "#777", "memory": "#7d3c98",
               "llm": "#555"}
STATUS_STYLE = {"READY": ("#2e8b57", "READY"), "MISSING_ITEMS": ("#c98a00", "MISSING ITEMS"),
                "NEEDS_HUMAN_REVIEW": ("#c0392b", "NEEDS HUMAN REVIEW")}
INST_LABEL = {"bank": "Bank deposits", "insurer": "Life insurance", "registry": "Shares"}
CAPACITY = {"Legal heir": "legal_heir", "Nominee": "nominee", "Joint holder": "joint_holder"}
DOC_NAME = {**DOC_CODES, "DOC_NOMINEE_KYC": "Claimant's ID (as nominee)"}
UPLOAD_DIR = ROOT / "data" / "uploads"

st.markdown("""<style>
.chip{display:inline-block;color:#fff;border-radius:10px;padding:1px 8px;font-size:12px;margin-right:6px}
.node{display:inline-block;border:1.5px solid #b8c4cc;border-radius:8px;padding:2px 8px;margin:2px;font-size:12px;color:#6b7885}
.node.done{background:#dcefef;border-color:#0b6e6e;color:#0b6e6e;font-weight:600}
.node.now{background:#fbefd9;border-color:#e8a33d;color:#8a5a00;font-weight:700}
.ev{padding:4px 0;border-bottom:1px solid #eef1f3;font-size:13.5px;line-height:1.35}
.ev .k{font-weight:700;margin-right:6px;font-size:12px;color:#444}
.warnmsg{color:#a93226}
.badge{color:#fff;border-radius:6px;padding:3px 10px;font-weight:700;font-size:13px}
.ok{color:#2e8b57;font-weight:700}.no{color:#a93226;font-weight:700}
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
ss.setdefault("up_gen", 0)          # bump to clear the upload widgets
ss.setdefault("more_gen", 0)


def langfuse_up() -> bool:
    try:
        import httpx
        return httpx.get(os.getenv("LANGFUSE_HOST", "http://localhost:3001") + "/api/public/health", timeout=1).status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------- helpers
def save_uploads(files) -> list[str]:
    """Store uploaded files under data/uploads/<hash of the set>/ and return their absolute paths (names are kept)."""
    if not files:
        return []
    h = hashlib.sha1()
    for f in sorted(files, key=lambda f: f.name):
        h.update(f.name.encode())
        h.update(f.getvalue())
    d = UPLOAD_DIR / h.hexdigest()[:12]
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(files, key=lambda f: f.name):
        p = d / Path(f.name).name
        if not p.exists():
            p.write_bytes(f.getvalue())
        out.append(str(p))
    return out


def render_events(ph) -> None:
    rows = []
    events = TRACE.events if ss.get("run") else []         # a fresh page shows nothing (the tracer is process-wide, not per visitor)
    for e in reversed(events):                            # newest first, so the live view always shows the latest step
        if e["kind"] == "NODE":
            continue
        col = AGENT_COLOR.get(e["agent"], "#555")
        warn = e["level"] == "warn" or any(w in e["message"] for w in ("UNFIT", "FAIL", "REJECTED", "ABSTAIN"))
        rows.append(f"<div class='ev'><span class='chip' style='background:{col}'>{e['agent']}</span>"
                    f"<span class='k'>{e['kind']}</span><span class='{'warnmsg' if warn else ''}'>{html.escape(e['message'])}</span></div>")
    ph.markdown("".join(rows) or "<i>No events yet. Upload the documents and press <b>Start</b>.</i>", unsafe_allow_html=True)


def render_stepper(ph, run) -> None:
    visited = set(run["visited"]) | {"read_documents"} if run else set()
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


def start_case(case: dict, use_llm: bool, fresh_memory: bool, key_dir: str | None = None, later: bool = False) -> dict:
    """case = {case_id, deceased, claimant, scans (absolute paths), claim_for}. A later session keeps the family's earlier answers."""
    saver = open_checkpointer()
    graph = build_graph(saver)
    clear_thread(saver, case["case_id"])
    if fresh_memory and not later:
        memory.forget(case["case_id"])
    llm.set_enabled(use_llm)
    if use_llm and not llm.warm_up():
        st.toast("Ollama model unavailable: using deterministic fallbacks", icon="⚠️")
    TRACE.configure(case["case_id"], echo=False, append=False)
    return {"graph": graph, "cfg": {"configurable": {"thread_id": case["case_id"]}}, "case": case, "key_dir": key_dir,
            "pending": None, "finished": False, "state": None, "visited": [], "next": [], "restarted": False, "later": later}


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


def graph_input(case: dict) -> dict:
    return {"case_id": case["case_id"], "deceased": case["deceased"], "claimant": case["claimant"], "scans": case.get("scans", []),
            "claim_for": case.get("claim_for", intake.CLAIM_FOR)}


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## Waris")
    st.caption("Agentic AI for unclaimed inheritance recovery. **Advisory only**: never files a claim, never decides heirship. All data is synthetic.")
    use_llm = st.checkbox(f"Use local LLM ({config.OLLAMA_MODEL})", value=True,
                          help="The LLM only chooses which portal to search next and helps word the letters. Off = fixed fallback order (still a full run).")
    fresh_mem = st.checkbox("Forget the family's earlier answers", value=True,
                            help="Untick and run the same family twice to see long-term memory skip the identity question.")
    st.divider()
    st.markdown(f"**Embeddings:** `{EMBED}`  \n**Langfuse:** {'on, [open](http://localhost:3001)' if langfuse_up() else 'off (local trace only)'}")
    st.markdown("**Limits:** rounds ≤ 6 · re-queries ≤ 2 · LLM calls ≤ 40 · timeout 10 s")
    with st.expander("For developers: run a benchmark case from its structured input"):
        _idx = {c["case_id"]: c for c in json.loads((config.CASES_DIR / "index.json").read_text(encoding="utf-8"))} \
            if (config.CASES_DIR / "index.json").exists() else {}
        dev_case = st.selectbox("Benchmark case", ["meena"] + list(_idx), format_func=lambda c: f"{c} · {_idx[c]['difficulty']}" if c in _idx else "meena · demo")
        dev_start = st.button("Run this case (skips the documents)", width="stretch")

tab_run, tab_rag, tab_eval, tab_graph = st.tabs(["File a claim", "Rules & RAG explorer", "Evaluation (60 cases)", "Graph & trace"])

# ================================================================ TAB 1: file a claim
with tab_run:
    run = ss.run
    left, right = st.columns([1, 1], gap="large")

    # ---------------- step 1 + 2: documents and the three fields
    with left:
        st.markdown("### 1 · Upload the proofs you have")
        st.caption("The deceased's **death certificate**, **your own ID** (KYC), a **proof of your relationship**, and any forms or "
                   "certificates you already hold. Photos or scans (PNG / JPG). Select several files at once.")
        files = st.file_uploader("Documents", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key=f"up{ss.up_gen}",
                                 label_visibility="collapsed")
        st.markdown("### 2 · About the claim")
        claim_for = st.multiselect("Which assets should Waris look for?", list(INST_LABEL), default=list(INST_LABEL),
                                   format_func=INST_LABEL.get, key=f"cf{ss.up_gen}")
        capacity = st.selectbox("I am claiming as", list(CAPACITY), key=f"ca{ss.up_gen}")
        others = st.text_input("Other names the deceased was known by (maiden name, spelling...)", placeholder="optional, comma separated",
                               key=f"on{ss.up_gen}")
        form = {"claim_for": claim_for or list(INST_LABEL), "claiming_as": CAPACITY[capacity], "other_names": others}

        paths = save_uploads(files)
        read = intake.read_uploads(paths) if paths else []
        built = intake.build_case(paths, form, reads=read) if paths else None

        if built:
            st.markdown("### 3 · What Waris read")
            ess = built["essentials"]
            st.markdown("  ".join(f"<span class='{'ok' if ess[k] else 'no'}'>{'✔' if ess[k] else '✘'} {lab}</span>" for k, lab in
                                  (("death_certificate", "death certificate"), ("claimant_id", "your ID"),
                                   ("relationship_proof", "proof of relationship"))), unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([{"file": r["file"], "recognised as": DOC_NAME.get(r["doc_code"], "not recognised"),
                                        "readable": "✔" if r["readable"] else "✘ " + r["reason"],
                                        "confidence": r["confidence"] if r["readable"] else None} for r in built["reads"]]),
                         hide_index=True, width="stretch")
            for issue in built["issues"]:
                st.warning(issue)
            c0 = built["case"]
            d0 = c0["deceased"] if c0 else {}
            k = hashlib.sha1("".join(paths).encode()).hexdigest()[:8]               # new files -> new widgets, prefilled again
            st.caption("Check what was read and correct anything wrong. What you type here is what Waris will use.")
            a1, a2 = st.columns(2)
            ov = {"deceased_name": a1.text_input("Deceased: full name", d0.get("name") or "", key=f"dn{k}"),
                  "deceased_dob": a2.text_input("Date of birth (YYYY-MM-DD, blank if unknown)", d0.get("dob") or "", key=f"db{k}"),
                  "deceased_dod": a1.text_input("Date of death (YYYY-MM-DD)", d0.get("dod") or "", key=f"dd{k}"),
                  "deceased_city": a2.text_input("City", d0.get("city") or "", key=f"dc{k}"),
                  "claimant_name": a1.text_input("Claimant: full name", c0["claimant"]["name"] if c0 else "", key=f"cn{k}"),
                  "relationship": a2.text_input("Relationship to the deceased", c0["claimant"]["relationship"] if c0 else "", key=f"cr{k}")}
            pre = {"deceased_name": d0.get("name") or "", "deceased_dob": d0.get("dob") or "", "deceased_dod": d0.get("dod") or "",
                   "deceased_city": d0.get("city") or "", "claimant_name": c0["claimant"]["name"] if c0 else "",
                   "relationship": c0["claimant"]["relationship"] if c0 else ""}
            typed = {a: b.strip() for a, b in ov.items() if b.strip() and b.strip() != pre[a]}          # only what the family changed
            final = intake.build_case(paths, form, override=typed, reads=read)
            for need in final["needs"]:
                st.error("Needed: " + need)
            srcs = final["sources"]
            if srcs:
                st.caption("Where each fact came from: " + "; ".join(f"{a.replace('_', ' ')} ← {b}" for a, b in srcs.items()))
            go = st.button("▶  Start", type="primary", width="stretch", disabled=final["case"] is None)
        else:
            final, go = None, False
            st.info("Upload the documents to begin. (For the demo: open a folder under `demo_proofs/`, select all its images, and read its README.txt for the three fields.)")

        # a second session: more documents arrive
        more_files, more_go = [], False
        if run and run["finished"] and final and final["case"]:
            st.markdown("### Add more documents")
            more_files = st.file_uploader("More documents", type=["png", "jpg", "jpeg"], accept_multiple_files=True,
                                          key=f"more{ss.more_gen}", label_visibility="collapsed")
            more_go = st.button("↻  Re-check with these documents", disabled=not more_files, width="stretch")

    # ---------------- right: pipeline + timeline
    with right:
        st.markdown("##### Pipeline")
        steps_ph = st.empty()
        st.markdown("##### Agent timeline (live, newest first)")
        ev_ph = st.container(height=520).empty()
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
    if go and final and final["case"]:
        ss.run = run = start_case(final["case"], use_llm, fresh_mem)
        with st.spinner("Running agents..."):
            drive(graph_input(run["case"]), ev_ph, steps_ph)
        st.rerun()
    elif more_go and more_files and final and final["case"]:
        case2 = {**final["case"], "scans": final["case"]["scans"] + save_uploads(more_files)}
        ss.run = run = start_case(case2, use_llm, fresh_mem, later=True)
        ss.more_gen += 1
        with st.spinner("Running agents with the new documents..."):
            drive(graph_input(run["case"]), ev_ph, steps_ph)
        st.rerun()
    elif dev_start:
        d = config.CASES_DIR / dev_case
        case = {**json.loads((d / "input.json").read_text(encoding="utf-8")), "claim_for": intake.CLAIM_FOR}
        ss.run = run = start_case(case, use_llm, fresh_mem, key_dir=str(d))
        with st.spinner("Running agents..."):
            drive(graph_input(run["case"]), ev_ph, steps_ph)
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
        if run and run["finished"]:
            state = run["state"]
            st.success(f"Done in {state.get('round', 0)} Verifier round(s), {state.get('llm_calls', 0)}/{config.MAX_LLM_CALLS} LLM calls. "
                       f"Released to family: **{'yes' if state.get('released') else 'no'}**")
            if state.get("scan_results"):
                st.markdown("##### Documents read by OCR")
                cols = st.columns(min(3, len(state["scan_results"])))
                for i, sr in enumerate(state["scan_results"]):
                    with cols[i % len(cols)]:
                        if sr.get("path") and Path(sr["path"]).exists():
                            st.image(sr["path"], width="stretch")
                        st.caption(f"{sr['file']}: " + (f"read as {DOC_NAME.get(sr['doc_code'], sr['doc_code'])} (conf {sr['confidence']})"
                                                       if sr["readable"] else f"unreadable ({sr['reason']}), not counted"))
            for c in state.get("doc_conflicts", []):
                st.error(f"Documents disagree: {c['scan']} shows {c['field']} '{c['scan_value']}' but the case says '{c['family_value']}'. "
                         "Waris does not pick one: a human decides.")
            if not state["claim_packs"]:
                st.info("**Nothing found.** No asset of this person was found in the sources you asked about. Waris does not invent assets.")
            for e in state.get("tool_errors", []):
                st.warning(f"{e['tool']} was unavailable ({e['error'][:60]}). Retry later or ask the institution directly.")
            st.markdown("##### Claim packs")
            for aid, pack in state["claim_packs"].items():
                color, label = STATUS_STYLE[pack["status"]]
                st.markdown(f"**{aid}** &nbsp; <span class='badge' style='background:{color}'>{label}</span>", unsafe_allow_html=True)
                if pack["requirements"]:
                    st.dataframe(pd.DataFrame([{"document": DOC_NAME.get(r["doc_code"], r["doc_code"]), "code": r["doc_code"],
                                                "cited rule": r["rule_id"], "family has it": "✔" if r["have_it"] else "✘ missing"}
                                               for r in pack["requirements"]]), hide_index=True, width="stretch")
                for n in pack["notes"]:
                    if n.startswith(("abstained", "escalated", "stopped")):
                        st.error(n)
            if state.get("letters"):
                st.markdown("##### Claim letters (drafts for the family to review)")
                for aid, text in state["letters"].items():
                    with st.expander(f"Letter for {aid}"):
                        st.code(text, language=None)
            if state.get("rejected_candidates"):
                with st.expander(f"Not claimed ({len(state['rejected_candidates'])} records rejected)"):
                    for r in state["rejected_candidates"]:
                        st.write(f"`{r['asset_id']}` {r['holder_name']}: {r['reason']} (score {r['score']})")
            key_dir = Path(run["key_dir"]) if run.get("key_dir") else None
            if key_dir is None:                                 # a benchmark family's proofs: find its answer key by the deceased's name
                slug = re.sub(r"[^a-z0-9]+", "_", run["case"]["deceased"]["name"].lower()).strip("_")
                idx_file = config.CASES_DIR / "index.json"
                if slug == "ramaswamy_subramanian":
                    key_dir = config.CASES_DIR / "meena"
                elif idx_file.exists():
                    hit = next((c["case_id"] for c in json.loads(idx_file.read_text(encoding="utf-8"))
                                if c["folder"].rsplit("_", 1)[0] == slug), None)
                    key_dir = config.CASES_DIR / hit if hit else None
            if key_dir and (key_dir / "answer_key.json").exists():
                s = score_case(state["claim_packs"], json.loads((key_dir / "answer_key.json").read_text(encoding="utf-8")), retrieval.rule_exists)
                st.markdown("##### Scorecard vs answer key (only for the benchmark cases)")
                m = st.columns(3)
                m[0].metric("Asset recall", f"{s['asset_recall']:.0%}")
                m[1].metric("Wrong-person matches", s["wrong_person_matches"], help="target 0")
                m[2].metric("Status accuracy", f"{s['status_accuracy']:.0%}")
                m = st.columns(3)
                m[0].metric("Checklist P / R", f"{s['checklist_precision']:.0%} / {s['checklist_recall']:.0%}")
                m[1].metric("Citation coverage", f"{s['citation_coverage']:.0%}")
                m[2].metric("Abstention correct", "yes" if s["abstention_correct"] else "no")

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
