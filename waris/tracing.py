"""Observability: every plan step, tool call, retrieval, grade, send-back and human pause is an event.

Three sinks, all fed from the same `event()` call and all PII-masked:
  1. coloured console log (what the audience watches during the demo)
  2. traces/<case>.jsonl + traces/<case>.html  (always written; works offline)
  3. Langfuse (optional; used when a server is reachable). session_id = case_id so the
     separate traces produced by a pause/resume are grouped together.
"""
import functools
import html
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from . import config
from .guardrails import mask_obj, mask_pii

_COLORS = {
    "supervisor": "\033[95m", "tracer": "\033[96m", "rules_expert": "\033[93m",
    "builder": "\033[92m", "verifier": "\033[91m", "human": "\033[97;44m",
    "guard": "\033[31m", "system": "\033[90m", "memory": "\033[35m",
}
_RESET = "\033[0m"
_HTML_COLORS = {
    "supervisor": "#8e5ea2", "tracer": "#0e8a9a", "rules_expert": "#c98a00", "builder": "#2e8b57",
    "verifier": "#c0392b", "human": "#1f4e9c", "guard": "#a93226", "system": "#777", "memory": "#7d3c98",
}


class Tracer:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.case_id = "case"
        self.echo = True
        self.out_dir: Path = config.TRACE_DIR
        self._lf = None
        self._lf_trace = None
        self._span = None
        self._t0 = time.time()

    # ---------- setup ----------
    def configure(self, case_id: str, out_dir: Optional[Path] = None, echo: bool = True,
                  langfuse: bool = True, append: bool = False) -> None:
        self.case_id, self.echo = case_id, echo
        self.out_dir = Path(out_dir) if out_dir else config.TRACE_DIR
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.events = []
        prior = self.out_dir / f"{case_id}.jsonl"
        if append and prior.exists():            # resumed run: keep the events from before the pause
            self.events = [json.loads(l) for l in prior.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.events.append({"t": 0, "agent": "system", "kind": "RESUME", "message":
                                "process restarted; resumed from checkpoint", "data": None, "level": "info"})
        self._t0 = time.time()
        self._lf = self._lf_trace = self._span = None
        if langfuse and os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            self._init_langfuse()

    def _init_langfuse(self) -> None:
        try:
            import httpx
            host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
            httpx.get(host + "/api/public/health", timeout=1.5).raise_for_status()
            from langfuse import Langfuse
            self._lf = Langfuse(host=host)
            self._lf_trace = self._lf.trace(name="waris-case", session_id=self.case_id,
                                            metadata={"synthetic_data": True})
        except Exception:
            self._lf = self._lf_trace = None     # offline: local trace still written

    @property
    def langfuse_on(self) -> bool:
        return self._lf_trace is not None

    # ---------- events ----------
    def event(self, agent: str, kind: str, message: str, data: Any = None, level: str = "info") -> None:
        msg = mask_pii(message)
        ev = {"t": round(time.time() - self._t0, 2), "agent": agent, "kind": kind,
              "message": msg, "data": mask_obj(data) if data is not None else None, "level": level}
        self.events.append(ev)
        if self.echo:
            col = _COLORS.get(agent, "")
            print(f"{col}[{kind:<8}]{_RESET} {col}{agent:<12}{_RESET} {msg}", flush=True)
        if self._lf_trace is not None:
            try:
                (self._span or self._lf_trace).event(name=f"{agent}.{kind}", input=ev["data"],
                                                     output=msg, level="WARNING" if level == "warn" else "DEFAULT")
            except Exception:
                pass

    def node(self, name: str):
        """Decorator for graph nodes: one span per node, timing + which state keys changed."""
        def deco(fn):
            @functools.wraps(fn)
            def wrapper(state):
                t = time.time()
                if self._lf_trace is not None:
                    try:
                        self._span = self._lf_trace.span(name=name)
                    except Exception:
                        self._span = None
                try:
                    out = fn(state)
                finally:
                    dt = round(time.time() - t, 2)
                    self.events.append({"t": round(time.time() - self._t0, 2), "agent": "system",
                                        "kind": "NODE", "message": f"{name} finished in {dt}s",
                                        "data": None, "level": "debug"})
                    if self._span is not None:
                        try:
                            self._span.end()
                        except Exception:
                            pass
                        self._span = None
                return out
            return wrapper
        return deco

    # ---------- outputs ----------
    def finish(self) -> dict:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        jl = self.out_dir / f"{self.case_id}.jsonl"
        with jl.open("w", encoding="utf-8") as f:
            for e in self.events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        page = self.out_dir / f"{self.case_id}.html"
        page.write_text(self._html(), encoding="utf-8")
        if self._lf is not None:
            try:
                self._lf.flush()
            except Exception:
                pass
        return {"jsonl": str(jl), "html": str(page), "langfuse": self.langfuse_on}

    def _html(self) -> str:
        rows = []
        for e in self.events:
            if e["kind"] == "NODE":
                continue
            c = _HTML_COLORS.get(e["agent"], "#555")
            data = f"<pre>{html.escape(json.dumps(e['data'], indent=1, ensure_ascii=False))}</pre>" if e["data"] else ""
            rows.append(
                f"<tr><td>{e['t']}s</td><td><span class='chip' style='background:{c}'>{e['agent']}</span></td>"
                f"<td><b>{e['kind']}</b></td><td>{html.escape(e['message'])}{data}</td></tr>")
        return f"""<!doctype html><meta charset='utf-8'><title>Waris trace: {self.case_id}</title>
<style>body{{font:14px Calibri,Arial;margin:24px;color:#222}}h1{{color:#0b6e6e}}
table{{border-collapse:collapse;width:100%}}td{{padding:6px 10px;border-bottom:1px solid #e3e3e3;vertical-align:top}}
.chip{{color:#fff;padding:2px 8px;border-radius:10px;font-size:12px}}pre{{background:#f6f6f6;padding:6px;margin:4px 0;font-size:12px}}</style>
<h1>Waris trace: {self.case_id}</h1>
<p>Generated {datetime.now():%Y-%m-%d %H:%M}. All data synthetic; PII masked. {len(rows)} events.</p>
<table><tr><th>t</th><th>agent</th><th>event</th><th>detail</th></tr>{''.join(rows)}</table>"""


TRACE = Tracer()
