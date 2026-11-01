"""Document intake: OCR every scan the family supplied, credit the documents that are readable, flag the rest.

  * readable scan   -> the document counts as held (it is evidence, so it leaves the "missing" list)
  * unreadable scan -> NOT counted and never guessed at; the family is asked for a clearer copy
  * two documents disagree (death certificate date of birth or name vs what the family told us)
                    -> flagged as a conflict; Waris does not pick a side, the asset goes to a human
  * instruction-like text inside a scan ("ignore the rules...") -> treated as data and dropped (injection guard)
"""
from .. import config
from ..guardrails import flag_injection
from ..tools import ocr
from ..tracing import TRACE


@TRACE.node("doc_intake")
def doc_intake(state: dict) -> dict:
    scans = state.get("scans", [])
    if not scans:
        return {"scan_results": [], "docs_from_scans": [], "doc_conflicts": [], "scan_notes": []}
    case_dir = config.CASES_DIR / state["case_id"]
    dec = state["deceased"]
    names = [dec["name"], *dec.get("aliases", [])]
    results, docs, conflicts, notes = [], [], [], []
    for rel in scans:
        path = case_dir / rel
        if not path.exists():
            notes.append(f"scan {rel} not found")
            TRACE.event("tracer", "OCR", f"{rel}: file not found; ignored", level="warn")
            continue
        res = ocr.read_scan(path)
        if flag_injection(res["text"]):
            TRACE.event("tracer", "GUARD", f"instruction-like text inside scan {res['file']} treated as data and "
                        "dropped (prompt-injection guard)", level="warn")
        slim = {k: res[k] for k in ("file", "doc_code", "readable", "confidence", "fields", "reason")}
        results.append(slim)
        if not res["readable"]:
            notes.append(f"scan {res['file']} unreadable ({res['reason']}): ask the family for a clearer copy")
            TRACE.event("tracer", "OCR", f"{res['file']}: unreadable ({res['reason']}); NOT counted as a held document, "
                        "family asked for a clearer copy", level="warn", data=slim)
            continue
        docs.append(res["doc_code"])
        TRACE.event("tracer", "OCR", f"{res['file']}: {res['doc_code']} read (confidence {res['confidence']}); "
                    "counted as held", data=slim)
        if res["doc_code"] == "DOC_DEATH_CERT":
            f = res["fields"]
            if dec.get("dob") and f.get("dob") and f["dob"] != dec["dob"]:
                conflicts.append({"scan": res["file"], "field": "date of birth", "scan_value": f["dob"], "family_value": dec["dob"]})
            if f.get("name") and not any(ocr.name_matches(f["name"], n) for n in names):
                conflicts.append({"scan": res["file"], "field": "name", "scan_value": f["name"], "family_value": dec["name"]})
    for c in conflicts:
        TRACE.event("verifier", "GUARD", f"documents disagree: {c['scan']} shows {c['field']} {c['scan_value']} but the family "
                    f"gave {c['family_value']}; Waris will not pick one, the claim goes to a human", level="warn")
    return {"scan_results": results, "docs_from_scans": sorted(set(docs)), "doc_conflicts": conflicts, "scan_notes": notes}
