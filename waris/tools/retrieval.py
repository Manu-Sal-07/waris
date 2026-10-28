"""Agentic RAG tools: rule corpus loader, Chroma index, retrieval and fit grading.

Embeddings are an offline hashing bag-of-words vector (no model download, fully deterministic);
Review 3 can swap in `nomic-embed-text` via Ollama without touching callers.
Grading is two-stage: stage 1 is a metadata check (free, deterministic); stage 2 asks the LLM only
when metadata cannot decide. Similarity alone is never trusted: a nominee rule can be the *most
similar* chunk and still be the wrong procedure for a legal heir.
"""
import math
import os
import re
import zlib
from functools import lru_cache
from typing import Callable, Optional

import chromadb
import yaml

from .. import config

_STOP = {"the", "a", "an", "of", "to", "and", "or", "in", "for", "by", "is", "are", "be", "as", "on", "with", "that", "this"}
DIM = 1024


_cache: dict = {}


_active: str | None = None


def backend() -> str:
    """Active embedding backend: 'ollama' (nomic-embed-text) or 'hash'. WARIS_EMBEDDINGS=auto|ollama|hash.
    Decided once per index build so index and queries always use the same vector space."""
    return _active or "hash"


def _choose_backend() -> str:
    want = os.getenv("WARIS_EMBEDDINGS", "auto")
    if want == "hash":
        return "hash"
    try:
        import ollama
        ollama.Client(host=config.OLLAMA_HOST, timeout=15).embed(
            model=os.getenv("WARIS_EMBED_MODEL", "nomic-embed-text"), input="probe")
        return "ollama"
    except Exception:
        return "hash"


def embed(text: str) -> list[float]:
    """hash = offline bag-of-words vector (deterministic, no model). ollama = nomic-embed-text neural embedding."""
    if backend() == "ollama":
        if text not in _cache:
            import ollama
            _cache[text] = ollama.Client(host=config.OLLAMA_HOST, timeout=config.LLM_TIMEOUT).embed(
                model=os.getenv("WARIS_EMBED_MODEL", "nomic-embed-text"), input=text)["embeddings"][0]
        return _cache[text]
    return _hash_embed(text)


def _hash_embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if tok in _STOP:
            continue
        vec[zlib.crc32(tok.encode()) % DIM] += 1.0
    vec = [1 + math.log(v) if v > 0 else 0.0 for v in vec]
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


# ---------- corpus ----------
def load_rules() -> list[dict]:
    rules = []
    for p in sorted(config.RULES_DIR.glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm)
        meta["text"] = body.strip()
        meta["file"] = p.name
        rules.append(meta)
    return rules


@lru_cache(maxsize=1)
def rules_by_id() -> dict:
    return {r["rule_id"]: r for r in load_rules()}


def rule_exists(rule_id: str) -> bool:
    return rule_id in rules_by_id()


# ---------- index ----------
_collection = None


def index_rules(path=None):
    """(Re)build the persistent Chroma collection from data/rules/*.md. Idempotent."""
    global _collection
    global _active
    _active = _choose_backend()
    _cache.clear()
    client = chromadb.PersistentClient(path=str(path or config.CHROMA_DIR))
    try:
        client.delete_collection("waris_rules")
    except Exception:
        pass
    col = client.create_collection("waris_rules", metadata={"hnsw:space": "cosine"})
    rules = load_rules()
    col.add(
        ids=[r["rule_id"] for r in rules],
        embeddings=[embed(r["title"] + ". " + r["text"]) for r in rules],
        documents=[r["text"] for r in rules],
        metadatas=[{"rule_id": r["rule_id"], "institution_type": r["institution_type"], "applies_to": r["applies_to"],
                    "topic": r["topic"], "amount_band": r["amount_band"]} for r in rules],
    )
    _collection = col
    return col


def _col():
    return _collection if _collection is not None else index_rules()


def retrieve_rules(query: str, institution_type: str, topic: str, exclude_ids: Optional[list[str]] = None,
                   k: int = 1) -> list[dict]:
    """Top-k rule chunks for the query, filtered by institution + topic, skipping already-rejected rules."""
    where = {"$and": [{"institution_type": institution_type}, {"topic": topic}]}
    if exclude_ids:
        where["$and"].append({"rule_id": {"$nin": list(exclude_ids)}})
    res = _col().query(query_embeddings=[embed(query)], n_results=k, where=where)
    out = []
    for i, rid in enumerate(res["ids"][0]):
        rule = dict(rules_by_id()[rid])
        rule["distance"] = round(res["distances"][0][i], 3)
        out.append(rule)
    return out


# ---------- grading ----------
def grade_rule(facts: dict, rule: dict, llm_fn: Optional[Callable[[dict, dict], Optional[bool]]] = None) -> dict:
    """-> {"fits": bool, "reason": str, "stage": "metadata"|"llm"}.

    facts: institution_type, topic, claimant_type, nominee_alive (True/False/None), amount_band.
    """
    if rule["institution_type"] != facts["institution_type"]:
        return {"fits": False, "stage": "metadata",
                "reason": f"rule is for {rule['institution_type']}, case is {facts['institution_type']}"}
    if rule["topic"] != facts["topic"]:
        return {"fits": False, "stage": "metadata", "reason": f"rule topic is {rule['topic']}, need {facts['topic']}"}
    if rule["amount_band"] not in ("any", facts.get("amount_band", "any")):
        return {"fits": False, "stage": "metadata", "reason": f"rule is for {rule['amount_band']} amounts"}

    applies, ctype = rule["applies_to"], facts.get("claimant_type")
    if applies == "any":
        return {"fits": True, "stage": "metadata", "reason": "applies to any claimant"}
    if not ctype:
        if llm_fn:
            verdict = llm_fn(facts, rule)
            if verdict is not None:
                return {"fits": verdict, "stage": "llm", "reason": "borderline: decided by LLM grader"}
        return {"fits": False, "stage": "metadata", "reason": "claimant type unknown; cannot confirm fit"}
    if applies != ctype:
        return {"fits": False, "stage": "metadata", "reason": f"rule applies to a {applies}; claimant is a {ctype}"}
    if applies == "legal_heir" and facts.get("nominee_alive") is True:
        return {"fits": False, "stage": "metadata", "reason": "a living nominee exists; legal-heir route not applicable"}
    return {"fits": True, "stage": "metadata", "reason": f"rule applies to a {applies}; claimant is a {ctype}"}
