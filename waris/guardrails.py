"""Guardrails: PII masking, input validation, prompt-injection flagging, limit checks.

Safety rules covered here: 5 (mask PII), 6 (bounded), 7 (portal/OCR text is data, not instructions).
"""
import re
from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator

from . import config

# ---------- PII masking ----------
_LONG_DIGITS = re.compile(r"\b(\d{2,})(\d{4})\b")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_PHONE = re.compile(r"\b[6-9]\d{9}\b")


def mask_pii(text: str) -> str:
    """Account numbers / PAN / phone: keep last 4 only."""
    text = _PAN.sub(lambda m: "******" + m.group(0)[-4:], text)
    text = _PHONE.sub(lambda m: "******" + m.group(0)[-4:], text)
    return _LONG_DIGITS.sub(lambda m: "*" * len(m.group(1)) + m.group(2), text)


def mask_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return mask_pii(obj)
    if isinstance(obj, dict):
        return {k: mask_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [mask_obj(v) for v in obj]
    return obj


# ---------- prompt-injection ----------
_INJECTION = re.compile(
    r"(ignore (all |the |previous |above )?(rules|instructions)|disregard|mark (this )?(as )?ready|"
    r"you are now|system prompt|override|do not (verify|check))",
    re.I,
)


def flag_injection(text: Optional[str]) -> bool:
    return bool(text and _INJECTION.search(text))


# ---------- input validation ----------
class _Deceased(BaseModel):
    name: str
    aliases: list[str] = []
    dob: Optional[str] = None
    dod: Optional[str] = None
    city: Optional[str] = None
    addresses: list[str] = []

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("deceased name too short")
        return v

    @field_validator("dob", "dod")
    @classmethod
    def _iso(cls, v: Optional[str]) -> Optional[str]:
        if v:
            date.fromisoformat(v)          # raises on bad format
        return v


class _Claimant(BaseModel):
    name: str
    relationship: str
    claimant_type: Literal["nominee", "legal_heir", "joint_holder"]
    has_nomination: bool = False
    documents_available: list[str] = []


class CaseInput(BaseModel):
    case_id: str
    deceased: _Deceased
    claimant: _Claimant
    scans: list[str] = []


def validate_case_input(raw: dict) -> dict:
    """Input guardrail: required fields, ISO dates, enumerations. Raises ValueError on bad input."""
    from .doc_codes import is_valid
    case = CaseInput(**raw)
    bad = [d for d in case.claimant.documents_available if not is_valid(d)]
    if bad:
        raise ValueError(f"unknown document codes in documents_available: {bad}")
    return case.model_dump()


# ---------- limits ----------
def llm_budget_left(state: dict) -> bool:
    return state.get("llm_calls", 0) < config.MAX_LLM_CALLS


def rounds_left(state: dict) -> bool:
    return state.get("round", 0) < config.MAX_ROUNDS
