"""Finalize: status per asset from fixed code (never the LLM), then hand to the human approval gate.

An asset becomes NEEDS_HUMAN_REVIEW when Waris abstained ("I don't know"), the Verifier escalated it,
or a limit (rounds / LLM calls) stopped the run before its checks passed.
"""
from .. import config
from ..state import ClaimPack, Requirement
from ..tools.status import compute_status
from ..tracing import TRACE
from .rules_expert import accepted_assets


@TRACE.node("finalize")
def finalize(state: dict) -> dict:
    unresolved = set()
    limit = None
    if state.get("verdict") == "send_back":
        limit = ("round limit" if state.get("round", 0) >= config.MAX_ROUNDS else "LLM-call limit")
        unresolved = {f["asset_id"] for f in state.get("verifier_feedback", [])
                      if not f["ok"] and f["round"] == state.get("round", 0)}
        TRACE.event("verifier", "LIMIT", f"stopped by {limit}: unresolved assets -> NEEDS_HUMAN_REVIEW", level="warn")

    packs = {}
    for asset in accepted_assets(state):
        aid = asset["asset_id"]
        old = state.get("claim_packs", {}).get(aid)
        reqs = old["requirements"] if old else []
        notes = []
        if asset.get("identity_confirmed"):
            notes.append("identity confirmed by the family")
        for r in {x["rule_id"] for x in reqs}:
            notes.append(f"cites {r}")
        if aid in state.get("abstained", {}):
            notes.append("abstained: " + state["abstained"][aid])
        if aid in state.get("escalated", {}):
            notes.append("escalated: " + state["escalated"][aid])
        if aid in unresolved:
            notes.append(f"stopped by {limit} before checks passed")
        conflicts = state.get("doc_conflicts", [])
        for c in conflicts:
            notes.append(f"document conflict: {c['scan']} shows {c['field']} {c['scan_value']}, family said {c['family_value']}")
        notes += state.get("scan_notes", [])
        status = compute_status(reqs, abstained=aid in state.get("abstained", {}),
                                escalated=aid in state.get("escalated", {}), limit_hit=aid in unresolved,
                                conflict=bool(conflicts))
        pack = ClaimPack(asset_id=aid, status=status, requirements=[Requirement(**r) for r in reqs],
                         missing=[r["doc_code"] for r in reqs if not r["have_it"]], notes=sorted(notes))
        packs[aid] = pack.model_dump()
        detail = ", ".join(pack.missing) if status == "MISSING_ITEMS" else (
            state.get("abstained", {}).get(aid) or state.get("escalated", {}).get(aid)
            or ("documents conflict; a human must decide" if conflicts else ""))
        TRACE.event("supervisor", "RESULT", f"{aid}: {status}" + (f"  ({detail})" if detail else ""))
    if not packs and not state.get("tool_errors"):
        TRACE.event("supervisor", "RESULT", "no assets found for this person in any searched source; nothing is claimed "
                    "(Waris never invents assets)")
    for e in state.get("tool_errors", []):
        TRACE.event("supervisor", "RESULT", f"{e['tool']} was unavailable: the family should retry later or ask the "
                    "institution directly (not guessed)", level="warn")
    for rj in state.get("rejected_candidates", []):
        TRACE.event("supervisor", "RESULT", f"{rj['asset_id']}: not claimed ({rj['reason']})")
    return {"claim_packs": packs, "limit_hit": limit}
