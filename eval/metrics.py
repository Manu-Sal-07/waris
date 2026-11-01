"""Evaluation metrics against the generator's answer key (labels never come from an LLM).

Per-case formulas (see design document, section 6); raw counts are returned too so that results can be
micro-averaged over many cases:
  asset_recall        = true assets found / true assets                        (an abstained asset still counts as found)
  wrong_person        = claimed assets whose record is a namesake or not a true asset   (target: 0)
  status_accuracy     = assets with the correct status / true assets
  checklist_P / R     = micro precision / recall of document codes vs the key's required_docs
  citation_coverage   = requirements with a rule_id that exists in the corpus / all requirements   (target: 100%)
  abstention_correct  = NEEDS_HUMAN_REVIEW raised exactly where the key says so
  question metrics    = family questions asked vs the questions the key expects (HITL precision / recall)
"""


def _rid(asset_id: str) -> str:
    return asset_id.split(":", 1)[1]


def score_case(packs: dict, answer_key: dict, rule_exists=lambda rid: True, asked: list[str] | None = None,
               state: dict | None = None) -> dict:
    truth = {a["record_id"]: a for a in answer_key["assets"]}
    claimed = {_rid(aid): p for aid, p in packs.items()}

    found = [rid for rid in truth if rid in claimed]
    wrong = [rid for rid in claimed if rid not in truth]
    status_ok = [rid for rid in found if claimed[rid]["status"] == truth[rid]["status"]]

    tp = pred = true = 0
    for rid in found:
        got = {r["doc_code"] for r in claimed[rid]["requirements"]}
        want = set(truth[rid]["required_docs"])
        tp, pred, true = tp + len(got & want), pred + len(got), true + len(want)
    for rid in wrong:                                    # documents asked for a wrong asset are all false positives
        pred += len(claimed[rid]["requirements"])
    reqs = [r for p in claimed.values() for r in p["requirements"]]
    cited = [r for r in reqs if r.get("rule_id") and rule_exists(r["rule_id"])]
    key_abstain = {rid for rid, a in truth.items() if a["status"] == "NEEDS_HUMAN_REVIEW"}
    got_abstain = {rid for rid, p in claimed.items() if p["status"] == "NEEDS_HUMAN_REVIEW"}

    out = {
        "n_truth": len(truth), "n_found": len(found), "n_status_ok": len(status_ok),
        "tp": tp, "pred": pred, "true": true, "n_reqs": len(reqs), "n_cited": len(cited),
        "asset_recall": len(found) / len(truth) if truth else 1.0,
        "wrong_person_matches": len(wrong),
        "status_accuracy": len(status_ok) / len(truth) if truth else 1.0,
        "checklist_precision": tp / pred if pred else 1.0,
        "checklist_recall": tp / true if true else 1.0,
        "citation_coverage": len(cited) / len(reqs) if reqs else 1.0,
        "abstention_correct": key_abstain == got_abstain,
        "detail": {"found": found, "wrong": wrong, "status_ok": status_ok,
                   "bad_status": {rid: [claimed[rid]["status"], truth[rid]["status"]] for rid in found if rid not in status_ok}},
    }
    if asked is not None:
        want_q = set(answer_key.get("expected_questions", []))
        got_q = set(asked)
        out.update({"q_asked": len(got_q), "q_expected": len(want_q), "q_hit": len(got_q & want_q),
                    "question_precision": len(got_q & want_q) / len(got_q) if got_q else 1.0,
                    "question_recall": len(got_q & want_q) / len(want_q) if want_q else 1.0})
    if state is not None:
        out["conflict_ok"] = bool(state.get("doc_conflicts")) == bool(answer_key.get("doc_conflict"))
        out["tool_error_ok"] = bool(state.get("tool_errors")) == bool(answer_key.get("expect_tool_error"))
    return out
