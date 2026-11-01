"""Mock bank / insurer / share-registry portals (one FastAPI app, three routes). Synthetic data only.

Search is deliberately fuzzy so portals return noisy candidates, including namesakes, like real ones do.
A `case` query parameter selects that case's sandbox database (data/cases/<case>/portals.db); without it the
default demo database is used. A database may declare a fault (`fail_first_<table>` in its meta table):
the portal then answers HTTP 503 until the client's `attempt` counter reaches that number, which lets us show
retry and "source unavailable" behaviour deterministically.
"""
import re
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from rapidfuzz import fuzz

from waris import config

app = FastAPI(title="Waris mock portals (synthetic)")
_CASE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _db_path(case: Optional[str]) -> Path:
    if case:
        if not _CASE_ID.match(case):
            raise HTTPException(400, "bad case id")
        p = config.CASES_DIR / case / "portals.db"
        if p.exists():
            return p
    return config.PORTAL_DB


def _search(table: str, name: str, case: Optional[str], attempt: int) -> list[dict]:
    con = sqlite3.connect(_db_path(case))
    con.row_factory = sqlite3.Row
    try:
        meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.OperationalError:
        meta = {}
    if attempt < int(meta.get(f"fail_first_{table}", 0)):
        con.close()
        raise HTTPException(503, f"{table} portal temporarily unavailable")
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
def bank_search(name: str, dob: Optional[str] = None, city: Optional[str] = None,
                case: Optional[str] = None, attempt: int = 0):
    return {"records": _search("bank", name, case, attempt)}


@app.get("/insurer/search")
def insurer_search(name: str, dob: Optional[str] = None, policy_no: Optional[str] = None,
                   case: Optional[str] = None, attempt: int = 0):
    return {"records": _search("insurer", name, case, attempt)}


@app.get("/registry/search")
def registry_search(name: str, folio: Optional[str] = None, case: Optional[str] = None, attempt: int = 0):
    return {"records": _search("registry", name, case, attempt)}
