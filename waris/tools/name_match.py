"""Name matching and the identity-match policy (safety rule 3: never claim a match we are unsure of).

match_name: RapidFuzz plus hand-written variant rules (initials, spelling, word order, alias).
identity_score: combines name + DOB + city into accept / ask / reject.
"""
import re
from typing import Optional

from rapidfuzz import fuzz

from .. import config

_ALIAS = {"mohd": "mohammed", "muhammad": "mohammed", "md": "mohammed", "mohammad": "mohammed"}
_TITLES = {"shri", "smt", "sri", "mr", "mrs", "late", "dr"}


def _raw_tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", s.lower()) if t not in _TITLES]


def _tokens(s: str) -> list[str]:
    return [_ALIAS.get(t, t) for t in _raw_tokens(s)]


def _initials_match(short: list[str], long: list[str]) -> bool:
    """Every token of `short` is either an initial of an unused token in `long` or a close spelling of one;
    at least one token must be a full word (so 'R S' alone never matches)."""
    if not any(len(t) > 1 for t in short):
        return False
    used: set[int] = set()
    for t in short:
        hit = None
        for i, u in enumerate(long):
            if i in used:
                continue
            if (len(t) == 1 and u.startswith(t)) or (len(t) > 1 and fuzz.ratio(t, u) >= 88):
                hit = i
                break
        if hit is None:
            return False
        used.add(hit)
    return True


def match_name(a: str, b: str) -> dict:
    """-> {"score": 0..1, "variant_type": exact|initials|order|spelling|none}"""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return {"score": 0.0, "variant_type": "none"}
    if ta == tb:
        # same words only after folding transliterations (Mohd/Muhammad -> Mohammed): a spelling variant
        if _raw_tokens(a) != _raw_tokens(b):
            return {"score": 0.93, "variant_type": "spelling"}
        return {"score": 1.0, "variant_type": "exact"}
    if sorted(ta) == sorted(tb):
        return {"score": 0.92, "variant_type": "order"}
    for short, long_ in ((ta, tb), (tb, ta)):          # whichever side carries the initials
        if any(len(t) == 1 for t in short) and len(short) <= len(long_) and _initials_match(short, long_):
            return {"score": 0.88, "variant_type": "initials"}
    r = fuzz.ratio(" ".join(ta), " ".join(tb)) / 100
    if r >= 0.88:
        return {"score": round(min(r, 0.95), 2), "variant_type": "spelling"}
    return {"score": round(fuzz.token_sort_ratio(" ".join(ta), " ".join(tb)) / 100, 2), "variant_type": "none"}


def identity_score(deceased: dict, record: dict) -> dict:
    """Combine name, DOB and city. A DOB conflict is a namesake and is rejected outright.

    score = 0.5*name + 0.3*dob + 0.2*city   (missing field counts 0.5, conflicting city 0)
    >= 0.85 accept | 0.60-0.85 ask the family | < 0.60 reject.  A medium match is NEVER auto-accepted.
    """
    names = [deceased["name"], *deceased.get("aliases", [])]
    scored = [(match_name(n, record["holder_name"]), i) for i, n in enumerate(names)]
    best, best_i = max(scored, key=lambda t: (t[0]["score"], -t[1]))
    if best_i > 0 and best["variant_type"] == "exact":
        best = {"score": 0.92, "variant_type": "alias"}        # recorded under another name (e.g. maiden name)
    evidence = [f"name: '{record['holder_name']}' ~ '{deceased['name']}' -> {best['variant_type']} ({best['score']})"]

    d_dob, r_dob = deceased.get("dob"), record.get("dob")
    if d_dob and r_dob:
        dob_c = 1.0 if d_dob == r_dob else None
        evidence.append("dob: match" if dob_c else f"dob: CONFLICT ({r_dob} vs {d_dob})")
    else:
        dob_c = 0.5
        evidence.append("dob: not available on record")

    d_cities = {c.lower() for c in [deceased.get("city"), *deceased.get("addresses", [])] if c}
    r_city = (record.get("city") or "").lower()
    if not r_city or not d_cities:
        city_c = 0.5
        evidence.append("city: not available")
    elif r_city in d_cities:
        city_c = 1.0
        evidence.append(f"city: match ({record['city']})")
    else:
        city_c = 0.0
        evidence.append(f"city: differs (record {record['city']}, family knows {sorted(d_cities)})")

    score = round(config.W_NAME * best["score"] + config.W_DOB * (dob_c or 0) + config.W_CITY * city_c, 2)

    if dob_c is None:
        band, reason = "reject", "namesake: date of birth conflicts"
    elif best["score"] < config.MIN_NAME:
        band, reason = "reject", "name does not match"
    elif score >= config.ACCEPT_AT:
        band, reason = "accept", "strong match"
    elif score >= config.ASK_AT:
        band, reason = "ask", "medium match: family must confirm"
    else:
        band, reason = "reject", "weak match"
    return {"score": score, "band": band, "reason": reason, "variant": best["variant_type"],
            "name_score": best["score"], "evidence": evidence}
