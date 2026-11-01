"""Documents-first intake: turn the proofs a family uploads (plus three form fields) into a case.

The family uploads photos/scans: the deceased's death certificate, their own ID (KYC), a proof of relationship and any
other documents they hold. Waris reads every file with OCR, works out what each one is, and builds the case itself:

    death certificate     -> deceased name, date of birth (if recorded), date of death, city, other names
    claimant ID           -> claimant name
    relationship proof    -> claimant, relationship (and, if printed, the deceased's date of birth: cross-check)
    form fields           -> which institutions to check, the capacity the claimant claims in, other names

Whatever cannot be read falls back to what the family typed (the confirm screen), and is reported as such.
Nothing is guessed: a missing essential is listed in `needs`.
"""
import hashlib
import re
from pathlib import Path
from typing import Optional

from .tools import ocr

CLAIM_FOR = ["bank", "insurer", "registry"]
CLAIMING_AS = ["legal_heir", "nominee", "joint_holder"]
ESSENTIALS = {"death_certificate": "DOC_DEATH_CERT", "claimant_id": "DOC_CLAIMANT_KYC", "relationship_proof": "DOC_RELATIONSHIP_PROOF"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def list_proofs(folder: str | Path) -> list[str]:
    """Image files of a proof folder, in file-name order (01_..., 02_...). Sub-folders (e.g. `later`) are not included."""
    return [str(p) for p in sorted(Path(folder).iterdir()) if p.suffix.lower() in IMAGE_SUFFIXES]


def case_id_for(name: str, dob: Optional[str], dod: Optional[str]) -> str:
    """Stable id of a family's case: the same deceased person always maps to the same case (memory, checkpoints)."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "case"
    return f"{slug}-{hashlib.sha1(f'{name.lower()}|{dob}|{dod}'.encode()).hexdigest()[:6]}"


def read_uploads(paths: list[str]) -> list[dict]:
    """OCR every file. -> one dict per file: file, path, doc_code, readable, confidence, fields, entities, reason, text."""
    return [{**ocr.read_scan(p), "path": str(p)} for p in paths]


def _first(reads: list[dict], code: str) -> Optional[dict]:
    return next((r for r in reads if r["readable"] and r["doc_code"] == code), None)


def build_case(paths: list[str], form: Optional[dict] = None, override: Optional[dict] = None,
               fallback: Optional[dict] = None, reads: Optional[list[dict]] = None) -> dict:
    """-> {case, reads, essentials, issues, needs, sources}.   `case` is None until the deceased's name is known.

    form     claim_for (list of bank/insurer/registry), claiming_as (legal_heir/nominee/joint_holder), other_names (str or list)
    override values the family typed on the confirm screen; they win over what OCR read
    fallback values used only where OCR could not read the field (e.g. the death certificate is too blurry)
    keys of override / fallback: deceased_name, deceased_dob, deceased_dod, deceased_city, claimant_name, relationship
    """
    form, override, fallback = form or {}, override or {}, fallback or {}
    paths = [str(Path(p).resolve()) for p in paths]                       # the graph runs elsewhere: always absolute
    reads = reads if reads is not None else read_uploads(paths)
    death, kyc = _first(reads, "DOC_DEATH_CERT"), _first(reads, "DOC_CLAIMANT_KYC")
    rel = _first(reads, "DOC_RELATIONSHIP_PROOF") or _first(reads, "DOC_LEGAL_HEIR_CERT")
    de = death["entities"] if death else {}
    ke = kyc["entities"] if kyc else {}
    re_ = rel["entities"] if rel else {}

    sources: dict[str, str] = {}

    def pick(key: str, *ocr_vals: tuple[str, Optional[str]]) -> Optional[str]:
        if override.get(key):
            sources[key] = "typed on the confirm screen"
            return override[key]
        for origin, val in ocr_vals:
            if val:
                sources[key] = f"read from the {origin}"
                return val
        if fallback.get(key):
            sources[key] = "typed by the family (not readable on the documents)"
            return fallback[key]
        return None

    name = pick("deceased_name", ("death certificate", de.get("deceased_name")), ("relationship proof", re_.get("deceased_name")))
    dob = pick("deceased_dob", ("death certificate", de.get("deceased_dob")), ("relationship proof", re_.get("deceased_dob")))
    dod = pick("deceased_dod", ("death certificate", de.get("deceased_dod")))
    city = pick("deceased_city", ("death certificate", de.get("deceased_city")))
    cname = pick("claimant_name", ("claimant ID", ke.get("claimant_name")), ("relationship proof", re_.get("claimant_name")))
    relation = pick("relationship", ("relationship proof", re_.get("relationship"))) or "family member"

    others = form.get("other_names") or []
    if isinstance(others, str):
        others = [x.strip() for x in others.split(",") if x.strip()]
    aliases = [a for a in dict.fromkeys([de.get("aka"), *others]) if a and name and a.lower() != name.lower()]

    essentials = {k: _first(reads, code) is not None for k, code in ESSENTIALS.items()}
    essentials["relationship_proof"] = essentials["relationship_proof"] or _first(reads, "DOC_LEGAL_HEIR_CERT") is not None
    issues, needs = [], []
    for r in reads:
        if not r["doc_code"]:
            issues.append(f"{r['file']}: not recognised as a claim document ({r['reason']})")
        elif not r["readable"]:
            issues.append(f"{r['file']}: looks like a {r['doc_code']} but is unreadable ({r['reason']}); a clearer copy is needed")
    if not essentials["death_certificate"]:
        (issues if name and dod else needs).append("no readable death certificate: the deceased's details come from what was typed")
    if not essentials["claimant_id"]:
        issues.append("no readable claimant ID (KYC): the claim will list it as missing")
    if not essentials["relationship_proof"]:
        issues.append("no readable proof of relationship: the relationship comes from what was typed")
    if not name:
        needs.append("the deceased's name (upload the death certificate or type it)")
    if not cname:
        needs.append("the claimant's name (upload the claimant's ID or type it)")

    claim_for = [c for c in (form.get("claim_for") or CLAIM_FOR) if c in CLAIM_FOR] or list(CLAIM_FOR)
    claiming_as = form.get("claiming_as") if form.get("claiming_as") in CLAIMING_AS else "legal_heir"
    case = None
    if name and cname:
        city_ = city or None
        case = {"case_id": case_id_for(name, dob, dod), "claim_for": claim_for,
                "deceased": {"name": name, "aliases": aliases, "dob": dob, "dod": dod, "city": city_,
                             "addresses": [city_] if city_ else []},
                "claimant": {"name": cname, "relationship": relation, "claimant_type": claiming_as,
                             "has_nomination": claiming_as == "nominee", "documents_available": []},
                "scans": [str(p) for p in paths]}
    return {"case": case, "reads": reads, "essentials": essentials, "issues": issues, "needs": needs, "sources": sources}
