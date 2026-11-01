"""Builds the figures used by BOTH the PPT and the design document (draw once, reuse).

Run:  python docs/build_figures.py   -> docs/figures/fig1_architecture.png, fig2_graph.png, fig3_sequence.png,
                                        fig4_demo_log.png (from a real captured run, if docs/figures/demo_run.txt exists)
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
TEAL, TEAL_L, AMBER, AMBER_L = "#0B6E6E", "#DCEFEF", "#E8A33D", "#FBEFD9"
INK, GREY, RED, BLUE, GREEN, PURPLE = "#1F2D3D", "#7A8794", "#C0392B", "#1F4E9C", "#2E8B57", "#7D3C98"
plt.rcParams["font.family"] = "DejaVu Sans"


def box(ax, x, y, w, h, text, fc=TEAL_L, ec=TEAL, fs=9, bold=False, tc=INK, lw=1.4, ls="-"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", zorder=3, linespacing=1.25)


def arrow(ax, p, q, color=INK, rad=0.0, ls="-", lw=1.4, ms=11):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=1, shrinkA=0, shrinkB=0))


def canvas(w, h, title):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    ax.text(0.15, h - 0.15, title, fontsize=13, fontweight="bold", color=TEAL, va="top")
    return fig, ax


def save(fig, name, facecolor="white"):
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", facecolor=facecolor)
    plt.close(fig)


# ------------------------------------------------------------------ Fig 1: architecture
def fig_architecture():
    fig, ax = canvas(14.4, 7.0, "Waris: system architecture")
    for y, lab in ((6.1, "INTERFACE &\nGUARDS"), (4.0, "ORCHESTRATION\n(LangGraph)"), (2.3, "TOOLS"), (0.8, "DATA")):
        ax.text(0.2, y, lab, fontsize=8.5, color=GREY, fontweight="bold", va="center")
    box(ax, 4.2, 6.1, 2.9, 0.8, "HUMAN GATES\nidentity confirm · final release\n(LangGraph interrupt)", fc="#E4ECF7", ec=BLUE, fs=8.2)
    box(ax, 7.6, 6.1, 3.0, 0.8, "Family / claimant\nCLI now · Streamlit in Review 3", fc="white", ec=GREY, fs=8.8)
    box(ax, 11.0, 6.1, 2.9, 0.8, "GUARDRAILS\nPII mask · input check ·\ninjection flag · hard limits", fc="#F9E3E0", ec=RED, fs=8.2)
    arrow(ax, (7.6, 5.7), (7.6, 5.55), color=GREY)
    arrow(ax, (5.65, 5.95), (6.2, 5.55), color=BLUE, ls="--", lw=1)
    arrow(ax, (9.55, 5.95), (9.0, 5.55), color=RED, ls="--", lw=1)
    box(ax, 7.6, 5.27, 7.6, 0.55, "SUPERVISOR   plan · route · enforce limits · pause for the family",
        fc=TEAL, ec=TEAL, tc="white", bold=True, fs=9.5)
    xs = [3.4, 5.8, 8.2, 10.6]
    names = [("TRACER", "ReAct: LLM picks the portal,\nscores identity, rejects\nnamesakes"),
             ("RULES EXPERT", "Corrective RAG: retrieve →\ngrade → re-query ≤2 →\nabstain"),
             ("BUILDER", "cited checklist of\nDOC_* codes\n(pydantic-validated)"),
             ("VERIFIER", "5 fixed checks V1–V5,\nsend-back with reason,\n≤6 rounds")]
    for x, (n, d) in zip(xs, names):
        ver = n == "VERIFIER"
        box(ax, x, 3.95, 2.25, 1.45, f"{n}\n{d}", fc=AMBER_L if ver else TEAL_L, ec=AMBER if ver else TEAL, fs=8.2)
        arrow(ax, (x, 4.99), (x, 4.68), color=GREY, lw=1)
    arrow(ax, (9.33, 3.95), (9.47, 3.95), color=INK, lw=1.4)
    arrow(ax, (10.6, 3.22), (8.2, 3.22), color=RED, rad=-0.3, ls="--", lw=1.4)
    ax.text(9.4, 3.0, "send back", ha="center", fontsize=8, color=RED)
    tools = [("portal client\nsearch_bank/insurer/registry\ntimeout 10s · retry 2", 3.0, False),
             ("match_name +\nidentity_score\n(RapidFuzz + variant rules)", 5.3, False),
             ("retrieve_rules +\ngrade_rule\n(2-stage grading)", 7.6, False),
             ("compute_status\n(fixed code,\nno LLM)", 9.9, False),
             ("OCR · letters\n(Review 3)", 12.1, True)]
    for t, x, dashed in tools:
        box(ax, x, 2.15, 1.9 if dashed else 2.1, 0.95, t, fc="white", ec=TEAL, fs=7.8, ls="--" if dashed else "-")
    ax.text(11.6, 1.3, "LLM (Ollama, temperature 0): only chooses the\nnext tool and grades borderline rules",
            ha="center", fontsize=7.2, color=GREY, style="italic")
    for xa, xb in ((3.4, 3.0), (3.4, 5.3), (5.8, 7.6)):
        arrow(ax, (xa, 3.22), (xb, 2.63), color=GREY, lw=1)
    data = [("Mock portals\nFastAPI + SQLite\nbank · insurer · registry", 3.2, TEAL_L, TEAL),
            ("Rule corpus\n6 cited rule files\nChroma vector index", 6.0, TEAL_L, TEAL),
            ("Checkpoints (short-term)\nSqliteSaver · thread_id = case_id\nresume after a restart", 9.0, AMBER_L, AMBER),
            ("Case file (long-term)\nfamily answers,\npast results", 12.0, AMBER_L, AMBER)]
    for t, x, c, e in data:
        box(ax, x, 0.65, 2.6, 0.95, t, fc=c, ec=e, fs=8)
    arrow(ax, (3.0, 1.65), (3.2, 1.13), color=GREY, lw=1)
    arrow(ax, (7.6, 1.65), (6.2, 1.13), color=GREY, lw=1)
    ax.add_patch(FancyBboxPatch((13.45, 0.2), 0.6, 6.5, boxstyle="round,pad=0.02,rounding_size=0.1", fc=PURPLE, ec=PURPLE, zorder=2))
    ax.text(13.75, 3.45, "OBSERVABILITY  ·  Langfuse + local JSONL/HTML trace  ·  PII masked", rotation=90, ha="center",
            va="center", color="white", fontsize=9, fontweight="bold", zorder=3)
    save(fig, "fig1_architecture.png")


# ------------------------------------------------------------------ Fig 2: LangGraph graph
def fig_graph():
    fig, ax = canvas(14.6, 6.6, "Waris: LangGraph agent graph (real node names)")
    A, B, C = 5.0, 2.45, 0.8
    nodes = {"START": (0.7, A), "intake_validate": (2.5, A), "supervisor_plan": (4.55, A), "doc_intake": (6.45, A),
             "tracer": (8.3, A), "identity_gate": (10.2, A), "human_confirm": (12.7, A),
             "rules_expert": (10.2, B), "builder": (8.3, B), "verifier": (6.45, B), "finalize": (4.55, B), "draft_letters": (2.5, B),
             "final_approval": (2.5, C), "END": (4.55, C)}
    sty = {"START": ("white", GREY), "END": ("white", GREY), "human_confirm": ("#E4ECF7", BLUE), "final_approval": ("#E4ECF7", BLUE),
           "verifier": (AMBER_L, AMBER), "doc_intake": ("#E8F5E9", GREEN), "draft_letters": ("#E8F5E9", GREEN)}
    for n, (x, y) in nodes.items():
        fc, ec = sty.get(n, (TEAL_L, TEAL))
        box(ax, x, y, 0.9 if n in ("START", "END") else 1.7, 0.62, n, fc=fc, ec=ec, fs=8.4, bold=True)
    for xa, xb in ((1.15, 1.65), (3.35, 3.7), (5.4, 5.6), (7.3, 7.45), (9.15, 9.35)):
        arrow(ax, (xa, A), (xb, A))
    arrow(ax, (11.05, A + 0.1), (11.85, A + 0.1), color=BLUE)
    arrow(ax, (11.85, A - 0.12), (11.05, A - 0.12), color=BLUE, ls="--")
    ax.text(11.45, A + 0.4, "medium match", ha="center", fontsize=8, color=BLUE)
    arrow(ax, (10.2, A - 0.31), (10.2, B + 0.31))
    ax.text(10.32, 3.7, "identity settled", fontsize=8, color=INK)
    for xa, xb in ((9.35, 9.15), (7.45, 7.3), (5.6, 5.4), (3.7, 3.35)):
        arrow(ax, (xa, B), (xb, B), color=GREEN if xa == 5.6 else INK)
    ax.text(5.0, B + 0.42, "pass", ha="center", fontsize=8, color=GREEN)
    arrow(ax, (2.5, B - 0.31), (2.5, C + 0.31), color=BLUE)
    arrow(ax, (3.35, C), (4.1, C), color=BLUE)
    ax.text(3.72, C + 0.14, "approved", ha="center", fontsize=8, color=BLUE)
    arrow(ax, (6.45, B + 0.31), (8.2, B + 0.31), color=RED, rad=-0.6, ls="--")
    ax.text(7.35, 3.5, "V1 V2 V5", ha="center", fontsize=8.5, color=RED, fontweight="bold")
    arrow(ax, (6.2, B + 0.31), (10.0, B + 0.31), color=RED, rad=-0.8, ls="--")
    ax.text(8.1, 3.95, "V3", ha="center", fontsize=8.5, color=RED, fontweight="bold")
    legend = "\n".join([
        "Dashed red = Verifier send-back (round += 1, <= 6):   V3 name proof missing -> rules_expert   V1/V2/V5 uncited or invalid item -> builder",
        "   V4 unconfirmed identity -> identity_gate.   Blue = human interrupt (checkpointed, resumes with Command(resume=...)).",
        "Green = doc_intake reads scans with OCR (unreadable = not counted, conflicts flagged, injection text dropped);",
        "   draft_letters writes a validated claim letter for each claimable asset.",
        "Limits: round >= 6 or LLM calls >= 40 -> finalize; unresolved -> NEEDS_HUMAN_REVIEW. Same failure twice -> escalated.",
        "A medium identity match is never auto-accepted. Status is fixed code in finalize, never the LLM."])
    ax.text(6.0, 1.45, legend, fontsize=7.4, color=INK, va="top", ha="left", linespacing=1.4)
    save(fig, "fig2_graph.png")


# ------------------------------------------------------------------ Fig 3: sequence diagram of Meena's case
def fig_sequence():
    fig, ax = canvas(14.6, 8.2, "Waris: data flow for Meena's case (three moments + the feedback loop)")
    lanes = ["Family", "Supervisor", "Tracer", "Portals", "Rules Expert", "Rule corpus", "Builder", "Verifier"]
    xs = {n: 1.0 + i * 1.65 for i, n in enumerate(lanes)}
    top, bottom = 7.2, 0.5
    for n, x in xs.items():
        box(ax, x, top + 0.1, 1.45, 0.42, n, fc=TEAL, ec=TEAL, tc="white", fs=8.5, bold=True)
        ax.plot([x, x], [bottom, top - 0.12], color="#B8C4CC", lw=1, ls=":", zorder=0)
    msgs = [
        ("Family", "Supervisor", "case details + claimant is a legal heir", INK, None),
        ("Supervisor", "Tracer", "plan: bank · insurer · shares", INK, None),
        ("Tracer", "Portals", "LLM picks search_bank → 3 records", INK, None),
        ("Portals", "Tracer", "'R. Subramanian' = initials (0.94) ✔ · namesakes ✘ (DOB)", RED, "1"),
        ("Tracer", "Portals", "search_registry → name ok, address differs (0.65)", INK, None),
        ("Tracer", "Family", "Is this record your relative?  (interrupt, checkpointed)", BLUE, "3"),
        ("Family", "Tracer", "yes → saved to case file", BLUE, None),
        ("Supervisor", "Rules Expert", "claim procedure for each settled asset", INK, None),
        ("Rules Expert", "Rule corpus", "query #0 → BANK-NOM-01 (nominee rule)", INK, None),
        ("Rule corpus", "Rules Expert", "graded UNFIT → re-query → BANK-LH-01 FITS", AMBER, "2"),
        ("Rules Expert", "Builder", "insurance: no rule → ABSTAIN ('I don't know')", AMBER, None),
        ("Builder", "Verifier", "checklist of 5 DOC_* items, each cited", INK, None),
        ("Verifier", "Rules Expert", "V3 FAIL: name variant, no name proof → send back", RED, "loop"),
        ("Rules Expert", "Builder", "BANK-NAME-01 fits → name affidavit added", INK, None),
        ("Builder", "Verifier", "round 2: all checks pass", GREEN, None),
        ("Supervisor", "Family", "statuses by fixed code; release? (interrupt) → yes", BLUE, None),
    ]
    y = top - 0.62
    for i, (s_, r, text, col, tag) in enumerate(msgs):
        xs_, xr = xs[s_], xs[r]
        ax.add_patch(FancyArrowPatch((xs_, y), (xr, y), arrowstyle="-|>", mutation_scale=10, color=col, lw=1.5, zorder=2))
        ax.text((xs_ + xr) / 2, y + 0.07, text, ha="center", va="bottom", fontsize=7.4, color=col,
                bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9), zorder=4)
        ax.text(0.2, y, str(i + 1), fontsize=7, color=GREY, va="center")
        if tag:
            lab = {"1": "MOMENT 1", "2": "MOMENT 2", "3": "MOMENT 3", "loop": "FEEDBACK LOOP"}[tag]
            ax.text(14.45, y, lab, fontsize=7.6, color="white", fontweight="bold", ha="right", va="center",
                    bbox=dict(fc=col, ec="none", boxstyle="round,pad=0.25"))
        y -= 0.4
    save(fig, "fig3_sequence.png")


# ------------------------------------------------------------------ Fig 4: real run log as an image
_AGENT = {"supervisor": "#C39BD3", "tracer": "#5DD0DC", "rules_expert": "#F5CB5C", "builder": "#7FDBA0",
          "verifier": "#F28B82", "human": "#8AB4F8", "memory": "#D7A8E6", "system": "#9AA5B1"}


def _log_lines():
    src = OUT / "demo_run.txt"
    if not src.exists():
        return []
    lines = [l.rstrip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    keep = [l for l in lines if re.match(r"\[(PLAN|THINK|TOOL|MATCH|RAG|GRADE|REQUERY|ABSTAIN|BUILD|VERIFY|HUMAN|GUARD|MEMORY|RESULT)", l)]
    keep = [re.sub(r"\s{2,}", "  ", l) for l in keep]
    return [(l[:158] + "...") if len(l) > 158 else l for l in keep]


def _render_log(keep, name, caption):
    h = 0.235 * len(keep) + 0.8
    fig, ax = plt.subplots(figsize=(13.5, h))
    fig.patch.set_facecolor("#14202B")
    ax.set_facecolor("#14202B")
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(keep) + 1.2)
    ax.text(0.005, len(keep) + 0.6, caption, color="#9AA5B1", fontsize=8.5, family="monospace", va="center")
    for i, l in enumerate(keep):
        m = re.match(r"\[(\w+)\s*\]\s+(\w+)\s+(.*)", l)
        kind, agent, rest = (m.group(1), m.group(2), m.group(3)) if m else ("", "system", l)
        y = len(keep) - i
        col = _AGENT.get(agent, "#E6EDF3")
        warn = kind in ("ABSTAIN", "GUARD") or "UNFIT" in rest or "FAIL" in rest or "REJECTED" in rest
        ax.text(0.005, y, f"{kind:<8}", color=col, fontsize=7.4, family="monospace", va="center", fontweight="bold")
        ax.text(0.063, y, f"{agent:<12}", color=col, fontsize=7.4, family="monospace", va="center")
        ax.text(0.15, y, rest, color="#FFB4A9" if warn else "#E6EDF3", fontsize=7.4, family="monospace", va="center")
    save(fig, name, facecolor="#14202B")


def fig_log():
    keep = _log_lines()
    if keep:
        _render_log(keep, "fig4_demo_log.png", "$ python -m waris.run --case meena      (real captured run; synthetic data)")
        picks = [r"bank_deposit:B001 'R\. Subramanian' ACCEPTED", r"bank_deposit:B002 .*REJECTED", r"shares:R001 .*UNSURE",
                 r"R002 treated as data", r"shares:R001: family answered", r"BANK-NOM-01 UNFIT", r"BANK-LH-01 FITS",
                 r"life_insurance:I001: I don't know", r"FAIL V3", r"BANK-NAME-01 FITS", r"round 2: bank_deposit:B001 PASS",
                 r"bank_deposit:B001: MISSING_ITEMS", r"life_insurance:I001: NEEDS_HUMAN_REVIEW", r"shares:R001: MISSING_ITEMS"]
        sel = [next(l for l in keep if re.search(p, l)) for p in picks]
        _render_log(sel, "fig5_demo_excerpt.png", "$ python -m waris.run --case meena   (excerpt of a real run)")


if __name__ == "__main__":
    fig_architecture()
    fig_graph()
    fig_sequence()
    fig_log()
    print("figures written to", OUT)
