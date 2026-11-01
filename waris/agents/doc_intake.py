"""Document intake: OCR every document the family supplied, credit the ones that are readable, flag the rest.

  * readable document -> counts as a held document (it is evidence, so it leaves the "missing" list)
  * unreadable one    -> NOT counted and never guessed at; the family is asked for a clearer copy
  * documents that disagree with each other (the deceased's name or date of birth, the claimant's name or relationship)
                      -> flagged as a conflict; Waris does not pick a side, the asset goes to a human
  * instruction-like text inside a document ("ignore the rules...") -> treated as data and dropped (injection guard)
"""
from pathlib import Path

from .. import config
from ..guardrails import flag_injection
from ..tools import ocr
from ..tracing import TRACE


def _conflicts(res: dict, dec: dict, cl: dict) -> list[dict]:
    """Compare what one readable document says with the facts the case was built on."""
    e, out, f = res["entities"], [], res["file"]
    names = [dec["name"], *dec.get("aliases", [])]
    if e.get("deceased_name") and not any(ocr.name_matches(e["deceased_name"], n) for n in names):
        out.append({"scan": f, "field": "deceased's name", "scan_value": e["deceased_name"], "family_value": dec["name"]})
    if e.get("deceased_dob") and dec.get("dob") and e["deceased_dob"] != dec["dob"]:
        out.append({"scan": f, "field": "date of birth", "scan_value": e["deceased_dob"], "family_value": dec["dob"]})
    if e.get("claimant_name") and not ocr.name_matches(e["claimant_name"], cl["name"]):
        out.append({"scan": f, "field": "claimant's name", "scan_value": e["claimant_name"], "family_value": cl["name"]})
    if e.get("relationship") and cl.get("relationship") and cl["relationship"] != "family member" \
            and e["relationship"].strip().lower() != cl["relationship"].strip().lower():
        out.append({"scan": f, "field": "relationship", "scan_value": e["relationship"], "family_value": cl["relationship"]})
    return out


@TRACE.node("doc_intake")
def doc_intake(state: dict) -> dict:
    scans = state.get("scans", [])
    if not scans:
        return {"scan_results": [], "docs_from_scans": [], "doc_conflicts": [], "scan_notes": []}
    case_dir = config.CASES_DIR / state["case_id"]
    dec, cl = state["deceased"], state["claimant"]
    results, docs, conflicts, notes = [], [], [], []
    for rel in scans:
        path = Path(rel) if Path(rel).is_absolute() else case_dir / rel         # absolute = a file the family uploaded
        if not path.exists():
            notes.append(f"document {rel} not found")
            TRACE.event("tracer", "OCR", f"{rel}: file not found; ignored", level="warn")
            continue
        res = ocr.read_scan(path)
        if flag_injection(res["text"]):
            TRACE.event("tracer", "GUARD", f"instruction-like text inside {res['file']} treated as data and "
                        "dropped (prompt-injection guard)", level="warn")
        slim = {k: res[k] for k in ("file", "doc_code", "readable", "confidence", "fields", "reason")} | {"path": str(path)}
        results.append(slim)
        if not res["readable"]:
            what = f"looks like a {res['doc_code']}" if res["doc_code"] else "not recognised as a claim document"
            notes.append(f"{res['file']} {what} but is unreadable ({res['reason']}): ask the family for a clearer copy")
            TRACE.event("tracer", "OCR", f"{res['file']}: unreadable ({res['reason']}); NOT counted as a held document, "
                        "family asked for a clearer copy", level="warn", data=slim)
            continue
        code = res["doc_code"]
        if code == "DOC_CLAIMANT_KYC" and cl["claimant_type"] == "nominee":
            code = "DOC_NOMINEE_KYC"                    # the same ID proof, filed as the nominee's KYC
        docs.append(code)
        TRACE.event("tracer", "OCR", f"{res['file']}: {code} read (confidence {res['confidence']}); counted as held", data=slim)
        conflicts += _conflicts(res, dec, cl)
    for c in conflicts:
        TRACE.event("verifier", "GUARD", f"documents disagree: {c['scan']} shows {c['field']} '{c['scan_value']}' but the case says "
                    f"'{c['family_value']}'; Waris will not pick one, the claim goes to a human", level="warn")
    return {"scan_results": results, "docs_from_scans": sorted(set(docs)), "doc_conflicts": conflicts, "scan_notes": notes}
