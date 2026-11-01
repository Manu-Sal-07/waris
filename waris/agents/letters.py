"""Claim-letter drafting (after the statuses are final).

For every asset that is READY or MISSING_ITEMS Waris drafts a cover letter the family can review and send.
Facts are fixed: the letter lists exactly the documents the checklist says the family holds (enclosed) and the ones
still missing (to follow), cites nothing it cannot support and never states an amount or a promise.

Only the opening paragraph may be written by the LLM; the paragraph is validated (must name the deceased, the claimant
and the product; no numbers beyond the ones we supplied; short; no promises) and replaced by the template
paragraph when it fails. Assets that need a human (NEEDS_HUMAN_REVIEW) get no letter.
"""
import re

from .. import config, llm
from ..doc_codes import DOC_CODES
from ..guardrails import llm_budget_left, mask_pii
from ..tracing import TRACE

_ROLE = {"legal_heir": "a legal heir of the deceased (no nomination is registered)",
         "nominee": "the registered nominee of the deceased",
         "joint_holder": "the surviving joint holder of the account"}
_TO = {"bank": "The Manager, Deceased Customer Claims", "insurer": "The Manager, Death Claims Department",
       "registry": "The Registrar, Transmission Department"}
_FORBID = re.compile(r"guarantee|urgent|immediately|assure|promise|compensation|interest|penalt", re.I)

_SYSTEM = ("You write one short formal paragraph for a claim letter in Indian English. Use ONLY the facts supplied. "
           "Do not add any other name, number, date, amount or promise. 40 to 70 words. "
           'Reply with JSON only: {"paragraph": "..."}')


def letter_facts(state: dict, asset: dict, pack: dict) -> dict:
    rec, dec, cl = asset["record"], state["deceased"], state["claimant"]
    ref = mask_pii(str(rec.get("ref_no") or ""))
    return {"deceased": dec["name"], "dod": dec.get("dod") or "", "claimant": cl["name"], "relationship": cl["relationship"],
            "claimant_type": cl["claimant_type"], "product": rec["product"].split(" + ")[0].lower(),
            "holder": rec["holder_name"], "ref": ref, "inst": asset["institution_type"],
            "enclosed": [r["doc_code"] for r in pack["requirements"] if r["have_it"]],
            "to_follow": [r["doc_code"] for r in pack["requirements"] if not r["have_it"]]}


def template_paragraph(f: dict) -> str:
    return (f"I am {f['claimant']}, the {f['relationship']} of the late {f['deceased']}"
            + (f", who passed away on {f['dod']}" if f["dod"] else "")
            + f". I am {_ROLE[f['claimant_type']]}. I am writing to start the claim for the {f['product']}"
            + (f" (reference {f['ref']})" if f["ref"] else "")
            + f" held in the name of {f['holder']}, and I request your guidance on completing it.")


def paragraph_ok(par: str, f: dict) -> bool:
    if not isinstance(par, str) or not (25 <= len(par.split()) <= 90) or _FORBID.search(par):
        return False
    low = par.lower()
    if f["deceased"].lower() not in low or f["claimant"].lower() not in low or f["product"].split()[0] not in low:
        return False
    allowed = set(re.findall(r"\d+", f"{f['dod']} {f['ref']}"))
    return all(n in allowed for n in re.findall(r"\d+", par))


def render(f: dict, paragraph: str) -> str:
    def items(codes):
        return "\n".join(f"  {i}. {DOC_CODES[c]}" for i, c in enumerate(codes, 1)) or "  (none)"
    out = [f"To,\n{_TO[f['inst']]}", "",
           f"Subject: Claim for the {f['product']} of the late {f['deceased']}"
           + (f" (record held as '{f['holder']}')" if f["holder"] != f["deceased"] else ""),
           "", "Dear Sir/Madam,", "", paragraph, "",
           "Documents enclosed with this letter:", items(f["enclosed"]), "",
           "Documents I will submit shortly:" if f["to_follow"] else "No further documents are pending from my side.",
           items(f["to_follow"]) if f["to_follow"] else ""]
    if f["holder"] != f["deceased"]:
        have_aff = "DOC_NAME_VARIATION_AFFIDAVIT" in f["enclosed"]
        out += ["", f"Name difference: your record shows '{f['holder']}', while the death certificate shows '{f['deceased']}'. "
                    f"An affidavit that both names refer to the same person is {'enclosed' if have_aff else 'being arranged and will follow'}."]
    out += ["", "Kindly acknowledge receipt and tell me if anything else is required.", "", "Yours faithfully,", f["claimant"],
            f"({f['relationship']} of the deceased)", "",
            "Draft prepared with Waris (advisory tool). The claimant reviews and submits this letter; Waris files nothing."]
    return "\n".join(x for x in out if x is not None)


@TRACE.node("draft_letters")
def draft_letters(state: dict) -> dict:
    letters, llm_calls = {}, state.get("llm_calls", 0)
    assets = {a["asset_id"]: a for a in state.get("candidate_assets", [])}
    for aid, pack in state.get("claim_packs", {}).items():
        if pack["status"] == "NEEDS_HUMAN_REVIEW" or aid not in assets:
            continue
        f = letter_facts(state, assets[aid], pack)
        par, how = template_paragraph(f), "template"
        if config.LETTER_LLM and llm.enabled() and llm_budget_left({"llm_calls": llm_calls}):
            raw, used, _ = llm.chat_json(_SYSTEM, "Facts: " + str({k: f[k] for k in ("deceased", "dod", "claimant", "relationship",
                                                                                    "claimant_type", "product", "holder", "ref")}))
            llm_calls += used
            cand = raw.get("paragraph") if isinstance(raw, dict) else None
            if cand and paragraph_ok(cand, f):
                par, how = cand.strip(), "LLM paragraph (validated)"
            elif raw is not None:
                TRACE.event("builder", "GUARD", f"{aid}: LLM letter paragraph failed validation; using the template", level="warn")
        letters[aid] = render(f, par)
        TRACE.event("builder", "LETTER", f"{aid}: letter drafted ({len(f['enclosed'])} enclosed, {len(f['to_follow'])} to follow; {how})")
    return {"letters": letters, "llm_calls": llm_calls}
