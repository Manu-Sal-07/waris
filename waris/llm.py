"""Thin local-LLM wrapper (Ollama). Returns parsed JSON or None, and always reports calls used.

The LLM is only ever asked for *small structured decisions* (which tool next, borderline rule fit).
Anything that decides a status, a citation or a limit is fixed code. If Ollama is down or the
JSON is invalid after one retry, callers use a deterministic fallback so a run never dies.
"""
import json
from typing import Optional

from . import config
from .tracing import TRACE

_disabled = not config.USE_LLM
_client = None


def disable() -> None:
    global _disabled
    _disabled = True


def enabled() -> bool:
    return not _disabled


def _get_client():
    global _client
    if _client is None:
        import ollama
        _client = ollama.Client(host=config.OLLAMA_HOST, timeout=config.LLM_TIMEOUT)
    return _client


def chat_json(system: str, user: str, model: Optional[str] = None, quiet: bool = False) -> tuple[Optional[dict], int, Optional[str]]:
    """-> (parsed_json_or_None, llm_calls_used, error_or_None). One retry on invalid JSON."""
    global _disabled
    if _disabled:
        return None, 0, "llm disabled"
    used, err = 0, None
    for attempt in range(2):
        used += 1
        try:
            r = _get_client().chat(
                model=model or config.OLLAMA_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                format="json",
                options={"temperature": config.LLM_TEMPERATURE, "seed": config.LLM_SEED, "num_predict": 200},
            )
            out = json.loads(r["message"]["content"])
            if not quiet:
                TRACE.event("llm", "LLM", f"{model or config.OLLAMA_MODEL} answered in {r.get('total_duration', 0) / 1e9:.1f}s "
                            f"({r.get('eval_count', '?')} tokens): {json.dumps(out)[:160]}",
                            data={"model": model or config.OLLAMA_MODEL, "prompt_system": system[:300],
                                  "prompt_user": user[:600], "response": out})
            return out, used, None
        except json.JSONDecodeError as e:
            err = f"invalid JSON ({e.msg})"
        except Exception as e:                      # connection refused, model missing, timeout
            _disabled = True                        # don't keep paying timeouts this run
            return None, used, f"llm unavailable: {type(e).__name__}"
    return None, used, err


def warm_up() -> bool:
    """Load the model before the run so the first real call is not a cold start. Disables the LLM on failure
    (callers then use deterministic fallbacks; the run never depends on it)."""
    global _disabled
    if _disabled:
        return False
    try:
        _get_client().chat(model=config.OLLAMA_MODEL, messages=[{"role": "user", "content": "ok"}],
                           options={"num_predict": 1}, keep_alive="30m")
        return True
    except Exception:
        _disabled = True
        return False


def set_enabled(flag: bool) -> None:
    """UI switch: turn the LLM on/off for the next run."""
    global _disabled
    _disabled = not flag
