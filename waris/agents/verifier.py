"""Verifier (reflection / critic loop): fixed, explainable checks over the Builder's work.

  V1  every requirement carries a rule_id
  V2  that rule_id exists in the corpus and really requires that document
  V3  a name variant was found, so the checklist must contain name-variation proof
  V4  a medium identity match must have been confirmed by the family
  V5  the pack validates against the ClaimPack schema

A failed check names the agent that can fix it (V3 -> rules_expert, V1/V2/V5 -> builder, V4 -> identity_gate).
The same failure twice for the same asset escalates it to NEEDS_HUMAN_REVIEW so the loop can never ping-pong.
"""
from pydantic import ValidationError

from .. import config
from ..state import ClaimPack
from ..tools import retrieval
from ..tracing import TRACE
from .rules_expert import accepted_assets

_NAME_PROOF = "DOC_NAME_VARIATION_AFFIDAVIT"
_VARIANTS = {"initials", "spelling", "order", "alias"}
_PRIORITY = ["identity_gate", "rules_expert", "builder"]


def check_asset(asset: dict, pack: dict | None) -> list[dict]:
    """Run V1-V5 on one asset. -> list of failures {check, reason, target, need?}."""
    fails = []
    if asset["match"]["band"] == "ask" and asset.get("identity_confirmed") is not True:
        fails.append({"check": "V4", "target": "identity_gate",
                      "reason": "medium identity match without the family's confirmation"})
    if pack is None:
        return fails + [{"check": "V5", "target": "builder", "reason": "no claim pack was built"}]
    reqs = pack["requirements"]
    uncited = [r["doc_code"] for r in reqs if not r.get("rule_id")]
    if uncited:
        fails.append({"check": "V1", "target": "builder", "reason": f"uncited item(s): {uncited}"})
    bad = [r["doc_code"] for r in reqs
           if r.get("rule_id") and (not retrieval.rule_exists(r["rule_id"])
                                    or r["doc_code"] not in retrieval.rules_by_id()[r["rule_id"]]["requires"])]
    if bad:
        fails.append({"check": "V2", "target": "builder", "reason": f"item(s) not backed by their cited rule: {bad}"})
    if asset["match"]["variant"] in _VARIANTS and _NAME_PROOF not in {r["doc_code"] for r in reqs}:
        fails.append({"check": "V3", "target": "rules_expert", "need": "name_variation",
                      "reason": f"name variant '{asset['match']['variant']}' was found but the checklist has no "
                                "name-variation proof"})
    try:
        ClaimPack(**pack)
    except ValidationError as e:
        fails.append({"check": "V5", "target": "builder", "reason": f"schema validation failed: {e.error_count()} error(s)"})
    return fails


@TRACE.node("verifier")
def verifier(state: dict) -> dict:
    rnd = state.get("round", 0) + 1
    if "no_verifier" in config.ABLATE:                    # experiment: the critic is switched off
        TRACE.event("verifier", "VERIFY", f"round {rnd}: Verifier disabled (ablation); work passes unchecked", level="warn")
        return {"verdict": "pass", "round": rnd}
    counts = dict(state.get("failure_counts", {}))
    escalated = dict(state.get("escalated", {}))
    need = {k: list(v) for k, v in state.get("need_rules", {}).items()}
    feedback = list(state.get("verifier_feedback", []))
    all_fails: list[dict] = []

    for asset in accepted_assets(state):
        aid = asset["asset_id"]
        if aid in state.get("abstained", {}) or aid in escalated:
            continue
        fails = check_asset(asset, state.get("claim_packs", {}).get(aid))
        passed = [c for c in ("V1", "V2", "V3", "V4", "V5") if c not in {f["check"] for f in fails}]
        if not fails:
            TRACE.event("verifier", "VERIFY", f"round {rnd}: {aid} PASS ({', '.join(passed)})")
            feedback.append({"round": rnd, "asset_id": aid, "ok": True})
            continue
        for f in fails:
            key = f"{aid}|{f['check']}"
            counts[key] = counts.get(key, 0) + 1
            if counts[key] >= 2:
                escalated[aid] = f"{f['check']} failed twice: {f['reason']}"
                TRACE.event("verifier", "LIMIT", f"{aid}: {f['check']} failed twice -> escalated to NEEDS_HUMAN_REVIEW "
                            "(no ping-pong)", level="warn")
                break
            TRACE.event("verifier", "VERIFY", f"round {rnd}: {aid} FAIL {f['check']}: {f['reason']} "
                        f"-> send back to {f['target']}", level="warn")
            feedback.append({"round": rnd, "asset_id": aid, "ok": False, **f})
            all_fails.append({**f, "asset_id": aid})
            if f.get("need"):
                need.setdefault(aid, [])
                if f["need"] not in need[aid]:
                    need[aid].append(f["need"])

    live = [f for f in all_fails if f["asset_id"] not in escalated]
    if not live:
        return {"verdict": "pass", "round": rnd, "failure_counts": counts,
                "escalated": escalated, "need_rules": need, "verifier_feedback": feedback}
    target = min((f["target"] for f in live), key=_PRIORITY.index)
    if rnd >= config.MAX_ROUNDS:
        TRACE.event("verifier", "LIMIT", f"round limit {config.MAX_ROUNDS} reached; unresolved assets become "
                    "NEEDS_HUMAN_REVIEW", level="warn")
    return {"verdict": "send_back", "next_target": target, "round": rnd, "failure_counts": counts,
            "escalated": escalated, "need_rules": need, "verifier_feedback": feedback}
