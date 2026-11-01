"""Mock bank / insurer / share-registry portals (one FastAPI app, three routes). Synthetic data only.

One shared database (config.PORTAL_DB) holds the records of every customer of every institution, so a search for one family
also returns other people with similar names, exactly like a real portal. Search is deliberately fuzzy.
A fault can be declared in the meta table as `fail_first:<table>:<searched name>` = N: the portal then answers HTTP 503 to
the first N attempts of a search for that name, which lets us show retry and "source unavailable" behaviour deterministically.
"""
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException
from rapidfuzz import fuzz

from waris import config

app = FastAPI(title="Waris mock portals (synthetic)")


def _norm(s: str) -> str:
    return s.lower().replace(".", "").strip()


def _search(table: str, name: str, attempt: int) -> list[dict]:
    con = sqlite3.connect(config.PORTAL_DB)
    con.row_factory = sqlite3.Row
    try:
        meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.OperationalError:
        meta = {}
    q = _norm(name)
    if attempt < int(meta.get(f"fail_first:{table}:{q}", 0)):
        con.close()
        raise HTTPException(503, f"{table} portal temporarily unavailable")
    rows = [dict(r) for r in con.execute(f"SELECT * FROM {table}")]
    con.close()
    out = []
    for r in rows:
        if fuzz.token_set_ratio(q, _norm(r["holder_name"])) >= 70:
            r["institution"] = table
            out.append(r)
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/bank/search")
def bank_search(name: str, dob: Optional[str] = None, city: Optional[str] = None, attempt: int = 0):
    return {"records": _search("bank", name, attempt)}


@app.get("/insurer/search")
def insurer_search(name: str, dob: Optional[str] = None, policy_no: Optional[str] = None, attempt: int = 0):
    return {"records": _search("insurer", name, attempt)}


@app.get("/registry/search")
def registry_search(name: str, folio: Optional[str] = None, attempt: int = 0):
    return {"records": _search("registry", name, attempt)}
