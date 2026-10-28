"""Long-term memory: the per-family case file (SQLite), separate from the graph checkpoints.

Short-term memory = graph state, checkpointed after every node (resume after a restart).
Long-term memory = this file: answers the family gave and past results. It survives a brand-new
run, so a family returning a week later is not asked the same identity question twice.
"""
import json
import sqlite3
from datetime import datetime

from . import config


def _con() -> sqlite3.Connection:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.CASE_FILE_DB)
    con.execute("CREATE TABLE IF NOT EXISTS answers(case_id TEXT, asset_id TEXT, confirmed INTEGER, ts TEXT, "
                "PRIMARY KEY(case_id, asset_id))")
    con.execute("CREATE TABLE IF NOT EXISTS results(case_id TEXT PRIMARY KEY, ts TEXT, summary TEXT)")
    return con


def load_answers(case_id: str) -> dict:
    con = _con()
    rows = con.execute("SELECT asset_id, confirmed, ts FROM answers WHERE case_id=?", (case_id,)).fetchall()
    con.close()
    return {a: {"confirmed": bool(c), "ts": ts} for a, c, ts in rows}


def save_answer(case_id: str, asset_id: str, confirmed: bool) -> None:
    con = _con()
    con.execute("INSERT OR REPLACE INTO answers VALUES (?,?,?,?)",
                (case_id, asset_id, int(confirmed), datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()


def save_result(case_id: str, summary: dict) -> None:
    con = _con()
    con.execute("INSERT OR REPLACE INTO results VALUES (?,?,?)",
                (case_id, datetime.now().isoformat(timespec="seconds"), json.dumps(summary)))
    con.commit()
    con.close()


def forget(case_id: str) -> None:
    con = _con()
    con.execute("DELETE FROM answers WHERE case_id=?", (case_id,))
    con.execute("DELETE FROM results WHERE case_id=?", (case_id,))
    con.commit()
    con.close()
