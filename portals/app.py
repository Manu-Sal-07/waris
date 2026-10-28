"""Mock bank / insurer / share-registry portals (one FastAPI app, three routes). Synthetic data only.

Search is deliberately fuzzy so portals return noisy candidates, including namesakes, like real ones do.
"""
import sqlite3
from typing import Optional

from fastapi import FastAPI
from rapidfuzz import fuzz

from waris import config

app = FastAPI(title="Waris mock portals (synthetic)")


def _search(table: str, name: str) -> list[dict]:
    con = sqlite3.connect(config.PORTAL_DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(f"SELECT * FROM {table}")]
    con.close()
    q = name.lower().replace(".", "")
    out = []
    for r in rows:
        if fuzz.token_set_ratio(q, r["holder_name"].lower().replace(".", "")) >= 70:
            r["institution"] = table
            out.append(r)
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/bank/search")
def bank_search(name: str, dob: Optional[str] = None, city: Optional[str] = None):
    return {"records": _search("bank", name)}


@app.get("/insurer/search")
def insurer_search(name: str, dob: Optional[str] = None, policy_no: Optional[str] = None):
    return {"records": _search("insurer", name)}


@app.get("/registry/search")
def registry_search(name: str, folio: Optional[str] = None):
    return {"records": _search("registry", name)}
