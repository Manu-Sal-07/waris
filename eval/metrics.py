"""Evaluation metrics against the generator's answer key (labels never come from an LLM).

Formulas (see design document, section 6):
  asset_recall        = true assets found / true assets
  wrong_person        = claimed assets whose record is a namesake or not a true asset   (target: 0)
  status_accuracy     = assets with correct status / true assets
  checklist_P / R     = micro precision / recall of document codes vs the key's required_docs
  citation_coverage   = requirements with a rule_id that exists in the corpus / all requirements   (target: 100%)
  abstention_correct  = NEEDS_HUMAN_REVIEW raised exactly where the key says so
"""


def _rid(asset_id: str) -> str:
    return asset_id.split(":", 1)[1]


def score_case(packs: dict, answer_key: dict, rule_exists=lambda rid: True) -> dict:
    truth = {a["record_id"]: a for a in answer_key["assets"]}
    claimed = {_rid(aid): p for aid, p in packs.items()}

    found = [rid for rid in truth if rid in claimed]
    wrong = [rid for rid in claimed if rid not in truth or rid in answer_key.get("namesake_record_ids", [])]
    status_ok = [rid for rid in found if claimed[rid]["status"] == truth[rid]["status"]]

    tp = pred = true = 0
    for rid in found:
        got = {r["doc_code"] for r in claimed[rid]["requirements"]}
        want = set(truth[rid]["required_docs"])
        tp, pred, true = tp + len(got & want), pred + len(got), true + len(want)
    reqs = [r for p in claimed.values() for r in p["requirements"]]
    cited = [r for r in reqs if r.get("rule_id") and rule_exists(r["rule_id"])]
    key_abstain = {rid for rid, a in truth.items() if a["status"] == "NEEDS_HUMAN_REVIEW"}
    got_abstain = {rid for rid, p in claimed.items() if p["status"] == "NEEDS_HUMAN_REVIEW"}

    return {
        "asset_recall": len(found) / len(truth) if truth else 1.0,
        "wrong_person_matches": len(wrong),
        "status_accuracy": len(status_ok) / len(truth) if truth else 1.0,
        "checklist_precision": tp / pred if pred else 1.0,
        "checklist_recall": tp / true if true else 1.0,
        "citation_coverage": len(cited) / len(reqs) if reqs else 1.0,
        "abstention_correct": key_abstain == got_abstain,
        "detail": {"found": found, "wrong": wrong, "status_ok": status_ok},
    }
