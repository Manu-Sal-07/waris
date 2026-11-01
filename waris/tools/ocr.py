"""OCR tool: reads one scanned document (PNG/JPG) and returns the document type, key fields and a confidence.

Engine: RapidOCR (ONNX, runs offline on CPU). Results are cached by file hash so a batch run reads each scan once.

Everything read from a scan is *data, never instructions*: callers only use the whitelisted fields below,
and the raw text is scanned for instruction-like content by the prompt-injection guard.
A scan counts as `readable` only when its document type is recognised AND the fields needed from that
document type were read with confidence >= MIN_CONF. Unreadable scans are never guessed at.
"""
import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from .. import config

MIN_CONF = 0.60
_HEADERS = {                       # header text (letters only, upper case) -> document code
    "DEATHCERTIFICATE": "DOC_DEATH_CERT",
    "LEGALHEIRCERTIFICATE": "DOC_LEGAL_HEIR_CERT",
    "IDENTITYPROOF": "DOC_CLAIMANT_KYC",
    "FIXEDDEPOSITRECEIPT": "DOC_FD_RECEIPT",
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


def read_scan(path: str | Path) -> dict:
    """-> {file, doc_code, readable, confidence, fields{name,dob,dod,...}, injection, reason, text}"""
    path = Path(path)
    lines = _raw_read(path)
    text = "\n".join(t for t, _ in lines)
    out = {"file": path.name, "doc_code": None, "readable": False, "confidence": 0.0, "fields": {},
           "injection": False, "reason": "", "text": text}
    if not lines:
        out["reason"] = "no text detected"
        return out
    header = _squash("".join(t for t, _ in lines[:2])).upper()
    best = max(((fuzz.partial_ratio(key, header), code) for key, code in _HEADERS.items()), key=lambda t: t[0])
    if best[0] >= 85:                               # tolerant of single-letter OCR slips (CERTIFICATE -> CERTIEICATE)
        out["doc_code"] = best[1]
    if not out["doc_code"]:
        out["reason"] = "document type not recognised"
        return out

    need: dict[str, dict[str, str]] = {       # doc code -> {field key: label printed on the document}
        "DOC_DEATH_CERT": {"name": "Name", "dob": "Date of Birth", "dod": "Date of Death"},
        "DOC_LEGAL_HEIR_CERT": {"name": "Name of deceased", "heir": "Heir"},
        "DOC_CLAIMANT_KYC": {"name": "Name", "id": "ID"},
        "DOC_FD_RECEIPT": {"name": "Account holder", "acct": "Account"},
    }[out["doc_code"]]
    confs = []
    for key, label in need.items():
        val, conf = _field(lines, label)
        if val:
            out["fields"][key] = val
            confs.append(conf)
    for key in ("dob", "dod"):
        if key in out["fields"]:
            m = _DATE.search(out["fields"][key])
            if m:
                out["fields"][key] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            else:
                del out["fields"][key]
                confs.pop()
    out["confidence"] = round(sum(confs) / len(confs), 2) if confs else 0.0
    missing = [k for k in need if k not in out["fields"]]
    if missing:
        out["reason"] = f"could not read: {', '.join(missing)}"
    elif out["confidence"] < MIN_CONF:
        out["reason"] = f"low confidence ({out['confidence']})"
    else:
        out["readable"] = True
    return out


def name_matches(read_name: Optional[str], expected: str, threshold: int = 85) -> bool:
    """Space-insensitive fuzzy comparison (OCR often glues words together)."""
    if not read_name:
        return False
    return fuzz.partial_ratio(_squash(read_name), _squash(expected)) >= threshold
