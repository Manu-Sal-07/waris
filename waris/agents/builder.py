"""Builder: turns the graded, cited rules into a per-asset checklist of document codes.

It adds only what retrieved rules require (every item carries its rule_id). It does not decide the
final status; that is fixed code in `finalize`. Output is validated against the ClaimPack schema.
"""
from ..state import ClaimPack, Requirement
from ..tools.status import compute_status
from ..tracing import TRACE
from .rules_expert import accepted_assets


@TRACE.node("builder")
def builder(state: dict) -> dict:
    have = set(state["claimant"].get("documents_available", [])) | set(state.get("docs_from_scans", []))
    packs = dict(state.get("claim_packs", {}))
    for asset in accepted_assets(state):
        aid = asset["asset_id"]
        if aid in state.get("abstained", {}) or aid in state.get("escalated", {}):
            continue
        reqs, seen = [], set()
        for rule in state.get("applicable_rules", {}).get(aid, []):
            for code in rule["requires"]:
                if code not in seen:
                    seen.add(code)
                    reqs.append(Requirement(doc_code=code, rule_id=rule["rule_id"], have_it=code in have))
        missing = [r.doc_code for r in reqs if not r.have_it]
        pack = ClaimPack(asset_id=aid, status=compute_status([r.model_dump() for r in reqs]),
                         requirements=reqs, missing=missing)
        packs[aid] = pack.model_dump()
        cites = sorted({r.rule_id for r in reqs})
        TRACE.event("builder", "BUILD", f"{aid}: checklist of {len(reqs)} document(s), {len(missing)} missing, "
                    f"cited to {', '.join(cites)}", data=[f"{r.doc_code} <- {r.rule_id}" for r in reqs])
    return {"claim_packs": packs}
