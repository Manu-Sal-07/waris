"""Portal client: HTTP calls to the three mock portals with timeout + retry.

Failure behaviour (documented in the design): retry twice, then return ok=False so the Tracer
records "source unavailable" instead of crashing. Tests swap `_client` for FastAPI's TestClient.
"""
from typing import Optional

import httpx

from .. import config

_client: Optional[httpx.Client] = None


def set_client(client: Optional[httpx.Client]) -> None:
    global _client
    _client = client


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=config.PORTAL_URL, timeout=config.TOOL_TIMEOUT)
    return _client


def _search(path: str, params: dict) -> dict:
    params = {k: v for k, v in params.items() if v}
    last = ""
    for attempt in range(config.TOOL_RETRIES + 1):
        try:
            r = _http().get(path, params=params, timeout=config.TOOL_TIMEOUT)
            r.raise_for_status()
            return {"ok": True, "records": r.json()["records"], "error": None, "attempts": attempt + 1}
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    return {"ok": False, "records": [], "error": last, "attempts": config.TOOL_RETRIES + 1}


def search_bank(name: str, dob: Optional[str] = None, city: Optional[str] = None) -> dict:
    return _search("/bank/search", {"name": name, "dob": dob, "city": city})


def search_insurer(name: str, dob: Optional[str] = None, policy_no: Optional[str] = None) -> dict:
    return _search("/insurer/search", {"name": name, "dob": dob, "policy_no": policy_no})


def search_registry(name: str, folio: Optional[str] = None) -> dict:
    return _search("/registry/search", {"name": name, "folio": folio})


TOOLS = {"search_bank": search_bank, "search_insurer": search_insurer, "search_registry": search_registry}
