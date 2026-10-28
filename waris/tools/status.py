"""Status is computed by fixed code, never by the LLM (reproducible, testable against the answer key)."""


def compute_status(requirements: list[dict], *, abstained: bool = False, escalated: bool = False,
                   identity_ok: bool = True, limit_hit: bool = False) -> str:
    """NEEDS_HUMAN_REVIEW if we abstained / escalated / identity unconfirmed / hit a limit;
    MISSING_ITEMS if any required document is not available; otherwise READY."""
    if abstained or escalated or not identity_ok or limit_hit or not requirements:
        return "NEEDS_HUMAN_REVIEW"
    if any(not r["have_it"] for r in requirements):
        return "MISSING_ITEMS"
    return "READY"
