"""Graph state (working memory) and the validated output schema.

State is plain JSON-able dicts so the SQLite checkpointer can persist it after every node.
`ClaimPack` is a pydantic model used to *validate* output (guardrail): every requirement
must carry a rule_id and a known document code; status must be one of three values.
"""
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, field_validator

from .doc_codes import is_valid

Status = Literal["READY", "MISSING_ITEMS", "NEEDS_HUMAN_REVIEW"]


class Requirement(BaseModel):
    doc_code: str
    rule_id: str                      # citation into the rule corpus (safety rule 4)
    have_it: bool

    @field_validator("doc_code")
    @classmethod
    def _known_code(cls, v: str) -> str:
        if not is_valid(v):
            raise ValueError(f"unknown document code {v}")
        return v

    @field_validator("rule_id")
    @classmethod
    def _cited(cls, v: str) -> str:
        if not v:
            raise ValueError("requirement without a rule_id")
        return v


class ClaimPack(BaseModel):
    asset_id: str
    status: Status
    requirements: list[Requirement]
    missing: list[str]
    notes: list[str] = []


class CaseState(TypedDict, total=False):
    case_id: str
    deceased: dict
    claimant: dict
    scans: list[str]
    claim_for: list[str]                   # institutions the family wants checked (bank / insurer / registry)
    plan: list[dict]                       # one task per asset type
    tools_done: list[str]
    candidate_assets: list[dict]           # accepted/ask candidates with match evidence
    rejected_candidates: list[dict]        # namesakes etc., with the reason
    tool_errors: list[dict]                # portal failures (source marked unavailable)
    applicable_rules: dict                 # asset_id -> list of graded rules (cited)
    need_rules: dict                       # asset_id -> topics the Verifier asked for
    abstained: dict                        # asset_id -> reason ("no trusted rule found")
    requery_count: dict                    # "asset_id|topic" -> re-queries used
    claim_packs: dict                      # asset_id -> ClaimPack dict
    verifier_feedback: list[dict]
    verdict: str                           # pass | send_back
    next_target: str
    failure_counts: dict                   # "asset_id|check" -> times failed
    escalated: dict                        # asset_id -> reason
    round: int                             # Verifier rounds used (max 6)
    llm_calls: int                         # capped per case
    human_answers: list[dict]
    memory_answers: dict                   # asset_id -> bool, loaded from long-term case file
    pending_human_question: Optional[str]
    scan_results: list[dict]               # OCR result per scan (type, fields, confidence, readable)
    docs_from_scans: list[str]             # documents evidenced by a readable scan
    doc_conflicts: list[dict]              # documents that disagree with the family's facts (never resolved by Waris)
    scan_notes: list[str]
    letters: dict                          # asset_id -> drafted claim letter
    limit_hit: Optional[str]
    released: Optional[bool]
    done: bool
