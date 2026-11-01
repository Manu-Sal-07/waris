"""Supervisor: validates input, plans one task per asset type, routes between agents, enforces limits.

Planning is deterministic (the asset types are known up front, so the plan can be audited);
the *routing after each step* is where the supervisor reacts to what agents observed.
"""
from .. import config, memory
from ..guardrails import validate_case_input
from ..tracing import TRACE

ASSET_PLAN = [
    {"asset_type": "bank_deposit", "institution_type": "bank", "tool": "search_bank"},
    {"asset_type": "life_insurance", "institution_type": "insurer", "tool": "search_insurer"},
    {"asset_type": "shares", "institution_type": "registry", "tool": "search_registry"},
]


@TRACE.node("intake_validate")
def intake_validate(state: dict) -> dict:
    case = validate_case_input({k: state[k] for k in ("case_id", "deceased", "claimant", "scans", "claim_for") if k in state})
    TRACE.event("supervisor", "GUARD", f"input validated for case '{case['case_id']}' "
                f"(deceased: {case['deceased']['name']}, claimant is a {case['claimant']['claimant_type']})")
    prior = memory.load_answers(case["case_id"])
    if prior:
        TRACE.event("memory", "MEMORY", f"case file found: {len(prior)} earlier family answer(s) on record")
    return {"deceased": case["deceased"], "claimant": case["claimant"], "scans": case["scans"], "claim_for": case["claim_for"],
            "memory_answers": prior, "round": state.get("round", 0), "llm_calls": state.get("llm_calls", 0),
            "tools_done": [], "candidate_assets": [], "rejected_candidates": [], "applicable_rules": {},
            "need_rules": {}, "abstained": {}, "requery_count": {}, "claim_packs": {}, "verifier_feedback": [],
            "failure_counts": {}, "escalated": {}, "human_answers": [], "done": False,
            "scan_results": [], "docs_from_scans": [], "doc_conflicts": [], "scan_notes": [], "letters": {}}


@TRACE.node("supervisor_plan")
def supervisor_plan(state: dict) -> dict:
    plan = [dict(t, status="pending") for t in ASSET_PLAN if t["institution_type"] in state.get("claim_for", ["bank", "insurer", "registry"])]
    TRACE.event("supervisor", "PLAN", "plan: one task per asset type the family asked about -> "
                + ", ".join(f"{t['asset_type']} ({t['tool']})" for t in plan),
                data={"limits": {"rounds": config.MAX_ROUNDS, "requery": config.MAX_REQUERY,
                                 "llm_calls": config.MAX_LLM_CALLS, "tracer_steps": config.MAX_TRACER_STEPS}})
    return {"plan": plan}


# ---------- routing (conditional edges) ----------
def route_identity(state: dict) -> str:
    """After the identity gate: ask the family if any medium match is unconfirmed, else go on."""
    pending = [a for a in state.get("candidate_assets", [])
               if a["match"]["band"] == "ask" and a.get("identity_confirmed") is None]
    return "human_confirm" if pending else "rules_expert"


def route_after_verifier(state: dict) -> str:
    """Pass -> finalize. Send-back -> the named agent, unless a limit is hit (then finalize, unresolved
    assets become NEEDS_HUMAN_REVIEW)."""
    if state.get("verdict") == "pass":
        return "finalize"
    if state.get("round", 0) >= config.MAX_ROUNDS or state.get("llm_calls", 0) >= config.MAX_LLM_CALLS:
        return "finalize"
    return state["next_target"]
