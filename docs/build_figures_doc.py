"""Figures for the DESIGN DOCUMENT only (the PPT keeps the larger figures from build_figures.py).

Each figure is drawn at the printed size (full text width, 17 cm = 6.69 in) with fonts of 7 pt or more, so the text
stays readable on paper. Coordinates are inches.

Run:  python docs/build_figures_doc.py  -> docs/figures/doc_fig1_architecture.png, doc_fig2_graph.png, doc_fig3_log.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
TEAL, TEAL_L, AMBER, AMBER_L = "#0B6E6E", "#DCEFEF", "#D9901A", "#FBEFD9"
INK, GREY, RED, BLUE, GREEN, PURPLE = "#1F2D3D", "#6B7885", "#C0392B", "#1F4E9C", "#2E8B57", "#7D3C98"
BLUE_L, RED_L = "#E4ECF7", "#F9E3E0"
plt.rcParams["font.family"] = "DejaVu Sans"
W = 6.69
BODY, HEAD = 7.2, 7.8


def canvas(h):
    fig = plt.figure(figsize=(W, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title=None, body="", fc=TEAL_L, ec=TEAL, tc=INK, ls="-", lw=1.0, title_fs=HEAD, body_fs=BODY):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.01,rounding_size=0.05",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
    if title and body:
        ax.text(x, y + h / 2 - 0.09, title, ha="center", va="top", fontsize=title_fs, fontweight="bold", color=tc, zorder=3)
        ax.text(x, y - 0.07, body, ha="center", va="center", fontsize=body_fs, color=tc, zorder=3, linespacing=1.25)
    else:
        ax.text(x, y, title or body, ha="center", va="center", fontsize=title_fs if title else body_fs,
                fontweight="bold" if title else "normal", color=tc, zorder=3, linespacing=1.25)


def arrow(ax, p, q, color=INK, rad=0.0, ls="-", lw=1.0, ms=8):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=1, shrinkA=0, shrinkB=0))


# ------------------------------------------------------------------ Figure 1: architecture
def fig_architecture():
    H = 4.75
    fig, ax = canvas(H)
    cx = [0.825, 2.375, 3.925, 5.475]
    bw = 1.45
    # rows (centre y)
    y_gate, y_sup, y_ag, y_tool, y_data = 4.30, 3.64, 2.78, 1.56, 0.62

    box(ax, 1.05, y_gate, 1.9, 0.66, "HUMAN GATES", "identity confirm\nfinal release (interrupt)", fc=BLUE_L, ec=BLUE)
    box(ax, 3.15, y_gate, 1.9, 0.66, "FAMILY / CLAIMANT", "case form now\nOCR of scans: Review 3", fc="white", ec=GREY)
    box(ax, 5.25, y_gate, 1.9, 0.66, "GUARDRAILS", "PII mask · input check\ninjection flag · limits", fc=RED_L, ec=RED)
    arrow(ax, (3.15, y_gate - 0.33), (3.15, y_sup + 0.17), color=GREY)
    arrow(ax, (1.55, y_gate - 0.33), (1.9, y_sup + 0.17), color=BLUE, ls="--")
    arrow(ax, (4.75, y_gate - 0.33), (4.4, y_sup + 0.17), color=RED, ls="--")
    box(ax, 3.15, y_sup, 6.1, 0.34, "SUPERVISOR:  plan · route · enforce limits · pause for the family", fc=TEAL, ec=TEAL, tc="white")

    agents = [("TRACER", "ReAct: LLM picks the\nportal; code scores\nidentity, drops namesakes"),
              ("RULES EXPERT", "Corrective RAG:\nretrieve · grade ·\nre-query ≤ 2 · abstain"),
              ("BUILDER", "cited checklist of\nDOC_* codes\n(pydantic-validated)"),
              ("VERIFIER", "checks V1–V5; sends\nweak work back with\na reason (≤ 6 rounds)")]
    for x, (t, b) in zip(cx, agents):
        ver = t == "VERIFIER"
        box(ax, x, y_ag, bw, 1.02, t, b, fc=AMBER_L if ver else TEAL_L, ec=AMBER if ver else TEAL)
        arrow(ax, (x, y_sup - 0.17), (x, y_ag + 0.51), color=GREY)
    arrow(ax, (cx[3] - 0.3, y_ag - 0.51), (cx[1] + 0.3, y_ag - 0.51), color=RED, rad=-0.14, ls="--", lw=1.1)

    tools = [("TOOLS", "portal client (timeout,\nretry) · name matcher ·\nidentity score"),
             ("TOOLS", "retrieve_rules ·\ngrade_rule\n(2-stage grading)"),
             ("CHECK", "ClaimPack schema\n(pydantic)"),
             ("TOOLS", "compute_status:\nfixed code, no LLM")]
    labels = ["Portal + matching", "Rule retrieval", "Schema", "Status"]
    for x, (_, b), lab in zip(cx, tools, labels):
        box(ax, x, y_tool, bw, 0.84, lab, b, fc="white", ec=TEAL)
    for x in (cx[0], cx[1]):
        arrow(ax, (x, y_ag - 0.51), (x, y_tool + 0.42), color=GREY)
    arrow(ax, (cx[2], y_ag - 0.51), (cx[2], y_tool + 0.42), color=GREY)
    arrow(ax, (cx[3] + 0.3, y_ag - 0.51), (cx[3] + 0.3, y_tool + 0.42), color=GREY)

    data = [("Mock portals", "FastAPI + SQLite\nbank · insurer · registry", TEAL_L, TEAL),
            ("Rule corpus", "6 cited rule files\nChroma + nomic-embed", TEAL_L, TEAL),
            ("Checkpoints", "SqliteSaver, thread_id =\ncase_id: resume after crash", AMBER_L, AMBER),
            ("Case file", "long-term memory:\nfamily answers, results", AMBER_L, AMBER)]
    for x, (t, b, fc, ec) in zip(cx, data):
        box(ax, x, y_data, bw, 0.76, t, b, fc=fc, ec=ec)
    arrow(ax, (cx[0], y_tool - 0.42), (cx[0], y_data + 0.38), color=GREY)
    arrow(ax, (cx[1], y_tool - 0.42), (cx[1], y_data + 0.38), color=GREY)
    ax.text(3.15, 0.07, "LLM (Llama 3.1 8B via Ollama, temperature 0) only chooses the next tool and grades borderline rules.",
            ha="center", va="bottom", fontsize=BODY, color=GREY, style="italic")
    ax.add_patch(FancyBboxPatch((6.3, 0.25), 0.3, H - 0.4, boxstyle="round,pad=0.01,rounding_size=0.05", fc=PURPLE, ec=PURPLE, zorder=2))
    ax.text(6.45, 0.25 + (H - 0.4) / 2, "OBSERVABILITY: Langfuse + local JSONL/HTML trace · PII masked", rotation=90,
            ha="center", va="center", color="white", fontsize=BODY, fontweight="bold", zorder=3)
    fig.savefig(OUT / "doc_fig1_architecture.png", dpi=230, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ Figure 2: graph
def fig_graph():
    H = 4.1
    fig, ax = canvas(H)
    r1, r2, r3 = 3.7, 2.05, 0.55
    h = 0.4

    def node(x, y, name, w=1.2, fc=TEAL_L, ec=TEAL):
        box(ax, x, y, w, h, name, fc=fc, ec=ec, title_fs=BODY + 0.3)

    node(0.42, r1, "START", 0.65, "white", GREY)
    node(1.72, r1, "intake_validate", 1.25)
    node(3.25, r1, "supervisor_plan", 1.25)
    node(4.75, r1, "tracer", 1.0)
    node(4.75, r2, "identity_gate", 1.2)
    node(6.0, r2, "human_confirm", 1.1, BLUE_L, BLUE)
    node(3.35, r2, "rules_expert", 1.15)
    node(1.98, r2, "builder", 0.95)
    node(0.65, r2, "verifier", 0.95, AMBER_L, AMBER)
    node(0.65, r3, "finalize", 0.95)
    node(2.1, r3, "final_approval", 1.3, BLUE_L, BLUE)
    node(3.4, r3, "END", 0.65, "white", GREY)

    arrow(ax, (0.75, r1), (1.1, r1)); arrow(ax, (2.35, r1), (2.62, r1)); arrow(ax, (3.88, r1), (4.25, r1))
    arrow(ax, (4.75, r1 - h / 2), (4.75, r2 + h / 2))
    arrow(ax, (5.35, r2 + 0.08), (5.45, r2 + 0.08), color=BLUE); arrow(ax, (5.45, r2 - 0.08), (5.35, r2 - 0.08), color=BLUE, ls="--")
    ax.text(5.4, r2 + 0.3, "medium match", ha="center", va="bottom", fontsize=BODY, color=BLUE)
    arrow(ax, (4.15, r2), (3.93, r2)); arrow(ax, (2.77, r2), (2.46, r2)); arrow(ax, (1.5, r2), (1.13, r2))
    arrow(ax, (0.65, r2 - h / 2), (0.65, r3 + h / 2), color=GREEN)
    ax.text(0.75, (r2 + r3) / 2, "pass", fontsize=BODY, color=GREEN, va="center")
    arrow(ax, (1.13, r3), (1.45, r3), color=BLUE); arrow(ax, (2.75, r3), (3.07, r3), color=BLUE)
    top = r2 + h / 2
    for x0, x1, rad, lab, lx in ((0.85, 1.9, -0.57, "V1 V2 V5", 2.05), (0.65, 3.25, -0.45, "V3", 2.0), (0.45, 4.6, -0.42, "V4", 3.2)):
        arrow(ax, (x0, top), (x1, top), color=RED, rad=rad, ls="--", lw=1.1)
        apex = abs(rad) * (x1 - x0) / 2
        ax.text(lx if lab != "V4" else 2.9, top + (apex if lab != "V1 V2 V5" else 0.0) + 0.05 + (0.25 if lab == "V1 V2 V5" else 0), lab, ha="center", va="bottom", fontsize=BODY, color=RED, fontweight="bold")
    notes = "\n".join([
        "Dashed red: Verifier send-back (≤ 6 rounds)",
        "  V1 V2 V5 → builder · V3 → rules_expert",
        "  V4 → identity_gate",
        "Blue: human interrupt; state checkpointed,",
        "  resumes with Command(resume=…)",
        "Limits (6 rounds, 40 LLM calls) → finalize;",
        "  unresolved assets → NEEDS_HUMAN_REVIEW",
        "Status is fixed code in finalize, never the LLM"])
    ax.text(3.95, 1.5, notes, fontsize=BODY, color=INK, va="top", ha="left", linespacing=1.3)
    fig.savefig(OUT / "doc_fig2_graph.png", dpi=230, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ Figure 3: excerpt of a real run
LOG = [  # (kind, agent, text, warn)  all lines are taken from the captured run in docs/figures/demo_run.txt
    ("THINK", "tracer", "LLM llama3.1:8b (1.7 s, 39 tokens) chose search_bank", False),
    ("MATCH", "tracer", "B001 'R. Subramanian' ACCEPTED: initials variant, score 0.94", False),
    ("MATCH", "tracer", "B002 'Ramaswamy Subramanian' REJECTED: namesake, DOB conflicts", True),
    ("MATCH", "tracer", "R001 UNSURE: must ask the family (score 0.65)", False),
    ("GUARD", "tracer", "instruction-like text in record R002 treated as data, dropped", True),
    ("HUMAN", "human", "shares:R001: family answered 'yes', identity confirmed", False),
    ("GRADE", "rules", "BANK-NOM-01 UNFIT: rule applies to a nominee; claimant is a legal_heir", True),
    ("GRADE", "rules", "BANK-LH-01 FITS (after re-query 1/2)", False),
    ("ABSTAIN", "rules", "life_insurance:I001: I don't know, no trusted rule; sent to a human", True),
    ("VERIFY", "verifier", "round 1: B001 FAIL V3: name variant but no name-variation proof", True),
    ("VERIFY", "verifier", "round 2: B001 PASS (V1, V2, V3, V4, V5) after BANK-NAME-01 added", False),
    ("RESULT", "supervisor", "B001 MISSING_ITEMS · I001 NEEDS_HUMAN_REVIEW · R001 MISSING_ITEMS", False),
]
_COL = {"tracer": "#5DD0DC", "rules": "#F5CB5C", "verifier": "#F28B82", "human": "#8AB4F8", "supervisor": "#C39BD3"}


def fig_log():
    n = len(LOG)
    H = 0.2 * n + 0.62
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor("#14202B")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.text(0.1, H - 0.2, "$ python -m waris.run --case meena      (excerpt of a real run; synthetic data)",
            color="#9AA5B1", fontsize=BODY, family="monospace", va="center")
    for i, (kind, agent, text, warn) in enumerate(LOG):
        y = H - 0.5 - i * 0.2
        col = _COL.get(agent, "#E6EDF3")
        ax.text(0.1, y, f"{kind:<7}", color=col, fontsize=BODY, family="monospace", va="center", fontweight="bold")
        ax.text(0.78, y, f"{agent:<10}", color=col, fontsize=BODY, family="monospace", va="center")
        ax.text(1.6, y, text, color="#FFB4A9" if warn else "#E6EDF3", fontsize=BODY, family="monospace", va="center")
    fig.savefig(OUT / "doc_fig3_log.png", dpi=230, facecolor="#14202B")
    plt.close(fig)


if __name__ == "__main__":
    fig_architecture()
    fig_graph()
    fig_log()
    print("doc figures written to", OUT)
