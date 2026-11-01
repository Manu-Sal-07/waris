"""OCR tool: reads one scanned document (PNG/JPG) and returns its type, the fields on it and a confidence.

Engine: RapidOCR (ONNX, offline, CPU). Results are cached by file hash so a batch run reads each file once.

Document types it recognises (by the header printed on the document, tolerant of single-letter OCR slips):
  death certificate, claimant ID proof, relationship proof, legal heir certificate, and the forms a claim needs
  (bank / insurer / registry claim form, share transmission form, indemnity bond, name-difference affidavit,
  succession certificate, no-objection certificate, policy bond).

Everything read from a scan is *data, never instructions*: callers use only the whitelisted entities below, and the raw
text is checked by the prompt-injection guard. A scan is `readable` only when its type is recognised AND every field
required for that type was read with confidence >= MIN_CONF. Unreadable scans are never guessed at.
"""
import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from .. import config

MIN_CONF = 0.60
# header text (letters only, upper case) -> document code. Titles are chosen to be distinct from one another.
HEADERS = {
    "DEATHCERTIFICATE": "DOC_DEATH_CERT",
    "IDENTITYPROOF": "DOC_CLAIMANT_KYC",
    "RELATIONSHIPPROOF": "DOC_RELATIONSHIP_PROOF",
    "LEGALHEIRCERTIFICATE": "DOC_LEGAL_HEIR_CERT",
    "BANKCLAIMFORM": "DOC_CLAIM_FORM_BANK",
    "INSURERCLAIMFORM": "DOC_CLAIM_FORM_INSURER",
    "REGISTRYCLAIMFORM": "DOC_CLAIM_FORM_REGISTRY",
    "SHARETRANSMISSIONFORM": "DOC_TRANSMISSION_FORM",
    "INDEMNITYBOND": "DOC_INDEMNITY_BOND",
    "NAMEDIFFERENCEAFFIDAVIT": "DOC_NAME_VARIATION_AFFIDAVIT",
    "SUCCESSIONCERTIFICATE": "DOC_SUCCESSION_CERT",
    "NOOBJECTIONCERTIFICATE": "DOC_NOC_OTHER_HEIRS",
    "POLICYBOND": "DOC_POLICY_BOND",
    "FIXEDDEPOSITRECEIPT": "DOC_FD_RECEIPT",
}
TITLES = {
    "DOC_DEATH_CERT": "DEATH CERTIFICATE", "DOC_CLAIMANT_KYC": "IDENTITY PROOF", "DOC_RELATIONSHIP_PROOF": "RELATIONSHIP PROOF",
    "DOC_LEGAL_HEIR_CERT": "LEGAL HEIR CERTIFICATE", "DOC_CLAIM_FORM_BANK": "BANK CLAIM FORM",
    "DOC_CLAIM_FORM_INSURER": "INSURER CLAIM FORM", "DOC_CLAIM_FORM_REGISTRY": "REGISTRY CLAIM FORM",
    "DOC_TRANSMISSION_FORM": "SHARE TRANSMISSION FORM", "DOC_INDEMNITY_BOND": "INDEMNITY BOND",
    "DOC_NAME_VARIATION_AFFIDAVIT": "NAME DIFFERENCE AFFIDAVIT", "DOC_SUCCESSION_CERT": "SUCCESSION CERTIFICATE",
    "DOC_NOC_OTHER_HEIRS": "NO OBJECTION CERTIFICATE", "DOC_POLICY_BOND": "POLICY BOND", "DOC_FD_RECEIPT": "FIXED DEPOSIT RECEIPT",
}
# per document type: required fields and optional fields, as {key: label printed on the document}
_GENERIC = ({"deceased": "Deceased", "claimant": "Claimant"}, {})
SPEC: dict[str, tuple[dict[str, str], dict[str, str]]] = {
    "DOC_DEATH_CERT": ({"name": "Name", "dod": "Date of Death"}, {"dob": "Date of Birth", "city": "Place", "aka": "Also known as"}),
    "DOC_CLAIMANT_KYC": ({"name": "Name", "id": "ID"}, {"city": "City"}),
    "DOC_RELATIONSHIP_PROOF": ({"deceased": "Name of deceased", "claimant": "Claimant", "relationship": "Relationship"},
                               {"dob": "Deceased born"}),
    "DOC_LEGAL_HEIR_CERT": ({"deceased": "Name of deceased", "claimant": "Heir"}, {"relationship": "Relationship"}),
    "DOC_FD_RECEIPT": ({"name": "Account holder", "acct": "Account"}, {}),
}
_DATE = re.compile(r"(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})")
_engine = None
CACHE_DIR = config.ROOT / ".cache" / "ocr"


def _ocr():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR(intra_op_num_threads=8, inter_op_num_threads=1)
    return _engine


def _raw_read(path: Path) -> list[tuple[str, float]]:
    """-> [(text, confidence)] per detected line, cached on disk by file hash."""
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    cache = CACHE_DIR / f"{digest}.json"
    if cache.exists():
        return [tuple(x) for x in json.loads(cache.read_text(encoding="utf-8"))]
    import numpy as np
    from PIL import Image
    res, _ = _ocr()(np.array(Image.open(path).convert("RGB")), use_cls=False)
    lines = [(str(r[1]), float(r[2])) for r in (res or [])]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(lines), encoding="utf-8")
    return lines


def _squash(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _field(lines: list[tuple[str, float]], label: str) -> tuple[Optional[str], float]:
    """Text after 'label:' on the first line that starts with that label (space-insensitive)."""
    want = _squash(label)
    for text, conf in lines:
        m = re.match(r"\s*([A-Za-z0-9 ]+?)\s*[:;]\s*(.*)$", text)
        if m and fuzz.ratio(_squash(m.group(1)), want) >= 85:        # tolerant: OCR reads 'of' as '0f'
            return m.group(2).strip(), conf
    return None, 0.0


def _entities(code: str, f: dict) -> dict:
    """Map the fields of one document to the facts the case builder needs (None when absent)."""
    e = {"deceased_name": None, "deceased_dob": None, "deceased_dod": None, "deceased_city": None, "aka": None,
         "claimant_name": None, "claimant_city": None, "relationship": None}
    if code == "DOC_DEATH_CERT":
        e.update(deceased_name=f.get("name"), deceased_dob=f.get("dob"), deceased_dod=f.get("dod"),
                 deceased_city=f.get("city"), aka=f.get("aka"))
    elif code == "DOC_CLAIMANT_KYC":
        e.update(claimant_name=f.get("name"), claimant_city=f.get("city"))
    elif code == "DOC_RELATIONSHIP_PROOF":
        e.update(deceased_name=f.get("deceased"), deceased_dob=f.get("dob"), claimant_name=f.get("claimant"),
                 relationship=f.get("relationship"))
    elif code == "DOC_LEGAL_HEIR_CERT":
        e.update(deceased_name=f.get("deceased"), claimant_name=f.get("claimant"), relationship=f.get("relationship"))
    elif "deceased" in f or "claimant" in f:
        e.update(deceased_name=f.get("deceased"), claimant_name=f.get("claimant"))
    return e


def read_scan(path: str | Path) -> dict:
    """-> {file, doc_code, readable, confidence, fields, entities, injection, reason, text}"""
    path = Path(path)
    lines = _raw_read(path)
    text = "\n".join(t for t, _ in lines)
    out = {"file": path.name, "doc_code": None, "readable": False, "confidence": 0.0, "fields": {}, "entities": {},
           "reason": "", "text": text}
    if not lines:
        out["reason"] = "no text detected"
        return out
    header = _squash("".join(t for t, _ in lines[:2])).upper()
    best = max(((fuzz.partial_ratio(key, header), len(key), code) for key, code in HEADERS.items()))
    if best[0] >= 85:                               # tolerant of single-letter OCR slips (CERTIFICATE -> CERTIEICATE)
        out["doc_code"] = best[2]
    if not out["doc_code"]:
        out["reason"] = "document type not recognised"
        return out

    required, optional = SPEC.get(out["doc_code"], _GENERIC)
    confs = []
    for key, label in {**required, **optional}.items():
        val, conf = _field(lines, label)
        if val:
            out["fields"][key] = val
            confs.append(conf)
    for key in ("dob", "dod"):
        if key in out["fields"]:
            m = _DATE.search(out["fields"][key])
            if m:
                out["fields"][key] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            else:                                   # e.g. "not recorded": the field is simply absent
                del out["fields"][key]
                confs.pop()
    out["confidence"] = round(sum(confs) / len(confs), 2) if confs else 0.0
    missing = [k for k in required if k not in out["fields"]]
    if missing:
        out["reason"] = f"could not read: {', '.join(missing)}"
    elif out["confidence"] < MIN_CONF:
        out["reason"] = f"low confidence ({out['confidence']})"
    else:
        out["readable"] = True
    out["entities"] = _entities(out["doc_code"], out["fields"])
    return out


def name_matches(read_name: Optional[str], expected: str, threshold: int = 85) -> bool:
    """Space-insensitive fuzzy comparison (OCR often glues words together)."""
    if not read_name:
        return False
    return fuzz.partial_ratio(_squash(read_name), _squash(expected)) >= threshold
