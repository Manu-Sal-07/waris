"""One-pass baseline for the A/B experiment (the thing Waris must beat to justify its agentic design).

Same tools as Waris (portal search, OCR crediting of readable scans, the rule corpus, the letter writer) but NONE of
the agentic decisions:
  * no identity policy and no human questions: the single best name match per institution is simply taken
  * no rule grading, no re-query, no abstention: the single most similar rule is trusted
  * one LLM call per asset turns that rule into a checklist; no Verifier checks it
  * no document-conflict detection, no memory, one pass only
"""
import json

from . import config, llm
from .agents.doc_intake import doc_intake
from .agents.letters import draft_letters
from .agents.rules_expert import _query, _facts
from .doc_codes import DOC_CODES
from .state import ClaimPack, Requirement
from .tools import portals, retrieval
from .tools.name_match import match_name
from .tools.status import compute_status
from .tracing import TRACE

_ASSET = {"bank": ("bank_deposit", "search_bank"), "insurer": ("life_insurance", "search_insurer"),
          "registry": ("shares", "search_registry")}
_SYSTEM = ("You turn a claim-procedure rule into the checklist of documents a family must submit. Return every code listed "
           "under 'Required codes in the rule' and no other codes. "
           'JSON only: {"documents": ["DOC_...", ...]}')


def run_baseline(case: dict) -> dict:
    """case = input.json contents (+ case_id). Returns a state-like dict with claim_packs, letters, counters."""
    state = {"case_id": case["case_id"], "deceased": case["deceased"], "claimant": case["claimant"],
             "scans": case.get("scans", []), "llm_calls": 0}
    state.update(doc_intake(state))
    state["doc_conflicts"] = []                            # the baseline does not compare documents
    dec, have = case["deceased"], set(case["claimant"].get("documents_available", [])) | set(state["docs_from_scans"])
    cands, packs, tools_done, errors = [], {}, [], []
    for inst, (atype, tool) in _ASSET.items():
        if inst not in case.get("claim_for", list(_ASSET)):
            continue
        res = portals.TOOLS[tool](name=dec["name"])
        tools_done.append(tool)
        if not res["ok"]:
            errors.append({"tool": tool, "error": res["error"]})
            continue
        scored = sorted(((max(match_name(n, r["holder_name"])["score"] for n in [dec["name"], *dec.get("aliases", [])]), r)
                         for r in res["records"]), key=lambda t: -t[0])
        if not scored or scored[0][0] < config.MIN_NAME:
            continue
        rec = scored[0][1]                                 # best name match wins; no date-of-birth or city check
        asset = {"asset_id": f"{atype}:{rec['record_id']}", "asset_type": atype, "institution_type": inst,
                 "record": {k: rec.get(k) for k in ("record_id", "holder_name", "dob", "city", "product", "amount_inr",
                                                    "nominee", "nominee_status", "ref_no")},
                 "match": {"band": "accept", "variant": "none"}, "identity_confirmed": None}
        facts = _facts(state, asset, "claim_procedure")
        rule = retrieval.retrieve_rules(_query(asset, facts, "claim_procedure", 0), inst, "claim_procedure", k=1)[0]
        codes = list(rule["requires"])
        if llm.enabled() and state["llm_calls"] < config.MAX_LLM_CALLS:
            raw, used, _ = llm.chat_json(_SYSTEM, f"Rule {rule['rule_id']}: {rule['text'][:500]} Required codes in the rule: "
                                         f"{rule['requires']}.")
            state["llm_calls"] += used
            if isinstance(raw, dict) and isinstance(raw.get("documents"), list):
                got = [c for c in raw["documents"] if c in DOC_CODES]
                if got:
                    codes = got
        reqs = [Requirement(doc_code=c, rule_id=rule["rule_id"], have_it=c in have) for c in dict.fromkeys(codes)]
        pack = ClaimPack(asset_id=asset["asset_id"], status=compute_status([r.model_dump() for r in reqs]),
                         requirements=reqs, missing=[r.doc_code for r in reqs if not r.have_it],
                         notes=[f"baseline: top rule {rule['rule_id']} trusted without grading"])
        packs[asset["asset_id"]] = pack.model_dump()
        cands.append(asset)
        TRACE.event("builder", "BUILD", f"baseline {asset['asset_id']}: {rule['rule_id']} -> {len(reqs)} documents")
    state.update({"candidate_assets": cands, "claim_packs": packs, "tools_done": tools_done, "tool_errors": errors,
                  "round": 0, "requery_count": {}, "verifier_feedback": [], "human_answers": []})
    state.update(draft_letters(state))
    return state
