"""Human-in-the-loop nodes (LangGraph interrupt): identity confirmation and final release approval.

A medium identity match is NEVER auto-accepted (safety rule 3). Everything before `interrupt()` must be
idempotent because LangGraph re-runs the node from the top when the run is resumed.
"""
from langgraph.types import interrupt

from .. import memory
from ..tracing import TRACE

YES = {"y", "yes", "true", "confirm", "confirmed", "1"}


def is_yes(ans) -> bool:
    return str(ans).strip().lower() in YES


def _pending(state: dict) -> list[dict]:
    return [a for a in state.get("candidate_assets", [])
            if a["match"]["band"] == "ask" and a.get("identity_confirmed") is None]


@TRACE.node("identity_gate")
def identity_gate(state: dict) -> dict:
    """Apply earlier family answers from the long-term case file so they are not asked twice."""
    mem = state.get("memory_answers", {})
    cands = [dict(a) for a in state.get("candidate_assets", [])]
    rejected = list(state.get("rejected_candidates", []))
    changed = False
    for a in cands:
        if a["match"]["band"] == "ask" and a.get("identity_confirmed") is None and a["asset_id"] in mem:
            ok = mem[a["asset_id"]]["confirmed"]
            a["identity_confirmed"] = ok
            changed = True
            TRACE.event("memory", "MEMORY", f"{a['asset_id']}: family already answered '{'yes' if ok else 'no'}' on "
                        f"{mem[a['asset_id']]['ts']}; not asking again")
    if not changed:
        return {}
    kept = []
    for a in cands:
        if a.get("identity_confirmed") is False:
            rejected.append({"asset_id": a["asset_id"], "holder_name": a["record"]["holder_name"],
                             "reason": "family said this is not the deceased", "score": a["match"]["score"],
                             "evidence": a["match"]["evidence"]})
        else:
            kept.append(a)
    return {"candidate_assets": kept, "rejected_candidates": rejected}


@TRACE.node("human_confirm")
def human_confirm(state: dict) -> dict:
    a = _pending(state)[0]
    rec = a["record"]
    question = (f"Is this record your relative? {a['asset_type']} '{rec['holder_name']}', {rec['product']}, "
                f"city {rec['city']}. {'; '.join(a['match']['evidence'])}")
    ans = interrupt({"kind": "confirm_identity", "asset_id": a["asset_id"], "question": question})
    # ---- runs only after the family has answered ----
    ok = is_yes(ans)
    memory.save_answer(state["case_id"], a["asset_id"], ok)
    TRACE.event("human", "HUMAN", f"{a['asset_id']}: family answered '{'yes' if ok else 'no'}' -> "
                f"{'identity confirmed' if ok else 'record dropped'}; saved to case file")
    cands, rejected = [], list(state.get("rejected_candidates", []))
    for c in state["candidate_assets"]:
        if c["asset_id"] == a["asset_id"]:
            if not ok:
                rejected.append({"asset_id": c["asset_id"], "holder_name": rec["holder_name"],
                                 "reason": "family said this is not the deceased", "score": c["match"]["score"],
                                 "evidence": c["match"]["evidence"]})
                continue
            c = {**c, "identity_confirmed": True}
        cands.append(c)
    return {"candidate_assets": cands, "rejected_candidates": rejected,
            "human_answers": state.get("human_answers", []) + [{"asset_id": a["asset_id"], "confirmed": ok}]}


@TRACE.node("final_approval")
def final_approval(state: dict) -> dict:
    summary = {aid: p["status"] for aid, p in state.get("claim_packs", {}).items()}
    ans = interrupt({"kind": "release_pack", "question": "Release this claim pack to the family for review? "
                     "(Waris never files anything itself.)", "summary": summary})
    ok = is_yes(ans)
    TRACE.event("human", "HUMAN", f"release approval: {'approved' if ok else 'declined'} (advisory output only; "
                "nothing is submitted to any institution)")
    memory.save_result(state["case_id"], {"statuses": summary, "released": ok})
    return {"released": ok, "done": True}
