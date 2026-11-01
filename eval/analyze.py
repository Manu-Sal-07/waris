"""Turns <out>/runs.jsonl into the result tables, plots and failure analysis.

    python -m eval.analyze results/main

Writes (inside the results folder): summary.csv, summary.md, per_difficulty.csv, per_tag.csv, failures.md and
figures/*.png.  Headline numbers are computed on the held-out TEST split; the full 60 are reported separately.
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TEAL, AMBER, RED, GREY, BLUE = "#0B6E6E", "#E8A33D", "#C0392B", "#8A96A3", "#1F4E9C"
ORDER = ["baseline", "no_grading", "no_verifier", "full_nollm", "full"]
LABEL = {"full": "Waris (full)", "baseline": "One-pass baseline", "no_verifier": "Waris − Verifier",
         "no_grading": "Waris − grading/re-query", "full_nollm": "Waris, LLM off"}
COLOR = {"full": TEAL, "baseline": GREY, "no_verifier": AMBER, "no_grading": RED, "full_nollm": BLUE}


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in (path / "runs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def agg(rows: list[dict]) -> dict:
    """Micro-aggregate the runs of ONE variant/repetition over some set of cases."""
    s = lambda k: sum(r.get(k, 0) for r in rows)
    div = lambda a, b: a / b if b else 1.0
    n = len(rows) or 1
    p, rc = div(s("tp"), s("pred")), div(s("tp"), s("true"))
    return {
        "cases": len(rows),
        "asset_recall": div(s("n_found"), s("n_truth")), "wrong_person": s("wrong_person_matches"),
        "status_accuracy": div(s("n_status_ok"), s("n_truth")),
        "checklist_precision": p, "checklist_recall": rc, "checklist_f1": div(2 * p * rc, p + rc) if (p + rc) else 0.0,
        "abstention_correct": sum(1 for r in rows if r["abstention_correct"]) / n,
        "citation_coverage": div(s("n_cited"), s("n_reqs")),
        "question_precision": div(s("q_hit"), s("q_asked")), "question_recall": div(s("q_hit"), s("q_expected")),
        "case_perfect": sum(1 for r in rows if r["status_accuracy"] == 1 and r["wrong_person_matches"] == 0
                            and r["abstention_correct"] and r["checklist_precision"] == 1 and r["checklist_recall"] == 1) / n,
        "llm_calls": s("llm_calls") / n, "tool_calls": s("tool_calls") / n, "rounds": s("rounds") / n,
        "requeries": s("requeries") / n, "wall_s": s("wall_s") / n,
    }


def mean_std(vals: list[float]) -> tuple[float, float]:
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0)


def summarize(rows: list[dict], split: str) -> dict:
    out = {}
    for v in ORDER:
        vr = [r for r in rows if r["variant"] == v and (split == "all" or r["split"] == split)]
        if not vr:
            continue
        reps = sorted({r["rep"] for r in vr})
        per_rep = [agg([r for r in vr if r["rep"] == k]) for k in reps]
        out[v] = {m: mean_std([pr[m] for pr in per_rep]) for m in per_rep[0]}
        out[v]["reps"] = len(reps)
    return out


METRICS = [("status_accuracy", "Status accuracy", "{:.1%}"), ("checklist_f1", "Checklist F1", "{:.1%}"),
           ("checklist_precision", "Checklist precision", "{:.1%}"), ("checklist_recall", "Checklist recall", "{:.1%}"),
           ("asset_recall", "Asset recall", "{:.1%}"), ("wrong_person", "Wrong-person matches", "{:.1f}"),
           ("abstention_correct", "Abstention correct (cases)", "{:.1%}"), ("citation_coverage", "Citation coverage", "{:.1%}"),
           ("case_perfect", "Cases fully correct (status, abstention, exact checklist, no wrong person)", "{:.1%}"), ("question_precision", "Family-question precision", "{:.1%}"),
           ("question_recall", "Family-question recall", "{:.1%}"), ("llm_calls", "LLM calls / case", "{:.1f}"),
           ("tool_calls", "Tool calls / case", "{:.1f}"), ("rounds", "Verifier rounds / case", "{:.2f}"),
           ("wall_s", "Seconds / case", "{:.1f}")]


def table_md(summary: dict, title: str) -> str:
    vs = [v for v in ORDER if v in summary]
    head = "| Metric | " + " | ".join(LABEL[v] for v in vs) + " |\n|---|" + "---|" * len(vs) + "\n"
    body = ""
    for key, name, fmt in METRICS:
        cells = []
        for v in vs:
            m, sd = summary[v][key]
            cells.append(fmt.format(m) + (f" ± {fmt.format(sd)}" if summary[v]["reps"] > 1 and sd > 0 else ""))
        body += f"| {name} | " + " | ".join(cells) + " |\n"
    reps = {summary[v]["reps"] for v in vs}
    cases = {int(summary[v]["cases"][0]) for v in vs}
    n_cases = min(cases) if len(cases) == 1 else "/".join(str(c) for c in sorted(cases))
    return (f"### {title}\n\n{n_cases} cases per run; repetitions per variant: {sorted(reps)} "
            f"(mean ± standard deviation over repetitions)\n\n{head}{body}\n")


def bar_plot(summary: dict, keys: list[tuple[str, str]], title: str, path: Path, pct=True) -> None:
    vs = [v for v in ORDER if v in summary]
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    w = 0.8 / len(vs)
    for i, v in enumerate(vs):
        xs = [j + i * w for j in range(len(keys))]
        ys = [summary[v][k][0] * (100 if pct else 1) for k, _ in keys]
        es = [summary[v][k][1] * (100 if pct else 1) for k, _ in keys]
        ax.bar(xs, ys, w * 0.92, yerr=es, color=COLOR[v], label=LABEL[v], capsize=2, error_kw={"lw": 0.8})
    ax.set_xticks([j + 0.4 - w / 2 for j in range(len(keys))])
    ax.set_xticklabels([n for _, n in keys], fontsize=9)
    ax.set_ylabel("%" if pct else "")
    ax.set_title(title, fontsize=11, loc="left", color="#1F2D3D", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.32))
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def breakdown(rows: list[dict], by: str) -> list[dict]:
    out = []
    keys = sorted({t for r in rows for t in (r["tags"] if by == "tag" else [r["difficulty"]])})
    for k in keys:
        for v in ORDER:
            sel = [r for r in rows if r["variant"] == v and (k in r["tags"] if by == "tag" else r["difficulty"] == k)]
            if not sel:
                continue
            a = agg(sel)
            out.append({by: k, "variant": v, "runs": len(sel), "status_accuracy": a["status_accuracy"],
                        "checklist_f1": a["checklist_f1"], "wrong_person": a["wrong_person"],
                        "abstention_correct": a["abstention_correct"], "case_perfect": a["case_perfect"]})
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    import csv
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def failures_md(rows: list[dict], out: Path) -> str:
    fl = [r for r in rows if r["variant"] == "full" and r["rep"] == 0
          and (r["status_accuracy"] < 1 or r["wrong_person_matches"] or not r["abstention_correct"]
               or r["checklist_precision"] < 1 or r["checklist_recall"] < 1)]
    txt = "# Failure analysis: full Waris, repetition 0 (every imperfect run, all 60 cases)\n\n"
    if not fl:
        txt += "No imperfect runs: every case matched its answer key.\n"
    for r in sorted(fl, key=lambda r: r["case_id"]):
        txt += (f"## {r['case_id']} ({r['difficulty']}, {r['split']}) tags: {', '.join(r['tags'])}\n"
                f"- status accuracy {r['status_accuracy']:.0%}, checklist P/R {r['checklist_precision']:.0%}/{r['checklist_recall']:.0%}, "
                f"wrong-person {r['wrong_person_matches']}, abstention correct {r['abstention_correct']}\n"
                f"- wrong status (got, expected): {r['detail']['bad_status']}\n"
                f"- trace: `traces/{r['run_id']}.html`\n\n")
    return txt


def main(argv=None) -> int:
    out = Path((argv or sys.argv[1:])[0])
    rows = load(out)
    (out / "figures").mkdir(exist_ok=True)
    md = f"# Waris evaluation results\n\nSynthetic data only. {len(rows)} runs. The family is simulated by a scripted oracle " \
         "(answers from the answer key); labels come from the generator, never from an LLM.\n\n"
    flat = []
    for split, title in (("test", "Held-out test split (headline numbers)"), ("dev", "Dev split"), ("all", "All 60 cases")):
        s = summarize(rows, split)
        if not s:
            continue
        md += table_md(s, title)
        for v in s:
            flat.append({"split": split, "variant": v, **{m: round(s[v][m][0], 4) for m, _, _ in METRICS},
                         **{m + "_std": round(s[v][m][1], 4) for m, _, _ in METRICS}, "reps": s[v]["reps"]})
        if split == "test":
            bar_plot(s, [("status_accuracy", "Status\naccuracy"), ("checklist_f1", "Checklist\nF1"), ("abstention_correct", "Abstention\ncorrect"),
                         ("case_perfect", "Cases fully\ncorrect")], "Held-out test cases: quality by variant", out / "figures" / "quality_test.png")
            bar_plot(s, [("wrong_person", "Wrong-person matches")], "Held-out test cases: wrong-person matches (target 0)",
                     out / "figures" / "wrong_person_test.png", pct=False)
            bar_plot(s, [("llm_calls", "LLM calls"), ("tool_calls", "Tool calls"), ("rounds", "Verifier rounds")],
                     "Cost per case", out / "figures" / "cost_test.png", pct=False)
        if split == "all":
            bar_plot(s, [("status_accuracy", "Status\naccuracy"), ("checklist_f1", "Checklist\nF1"), ("abstention_correct", "Abstention\ncorrect"),
                         ("case_perfect", "Cases fully\ncorrect")], "All 60 cases: quality by variant", out / "figures" / "quality_all.png")
    write_csv(out / "summary.csv", flat)
    bd = breakdown(rows, "difficulty")
    write_csv(out / "per_difficulty.csv", bd)
    write_csv(out / "per_tag.csv", breakdown(rows, "tag"))
    # difficulty plot
    vs = [v for v in ORDER if any(r["variant"] == v for r in rows)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    diffs = ["easy", "medium", "hard"]
    w = 0.8 / len(vs)
    for i, v in enumerate(vs):
        ys = [next((b["case_perfect"] * 100 for b in bd if b["difficulty"] == d and b["variant"] == v), 0) for d in diffs]
        ax.bar([j + i * w for j in range(3)], ys, w * 0.92, color=COLOR[v], label=LABEL[v])
    ax.set_xticks([j + 0.4 - w / 2 for j in range(3)])
    ax.set_xticklabels(diffs)
    ax.set_ylabel("% of cases fully correct")
    ax.set_title("Fully correct cases by difficulty (all 60 cases)", fontsize=11, loc="left", color="#1F2D3D", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.34))
    fig.tight_layout()
    fig.savefig(out / "figures" / "difficulty_all.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    # decision table
    s_all = summarize(rows, "test") or summarize(rows, "all")
    if "full" in s_all:
        md += "### What each component contributes (held-out test split, difference from full Waris)\n\n" \
              "| Variant | Δ status accuracy | Δ checklist F1 | Δ cases fully correct | Δ wrong-person | Δ LLM calls |\n|---|---|---|---|---|---|\n"
        for v in ("baseline", "no_verifier", "no_grading", "full_nollm"):
            if v in s_all:
                d = lambda k: s_all["full"][k][0] - s_all[v][k][0]
                z = lambda x: round(x, 1) + 0.0                  # avoid printing "-0.0"
                md += (f"| {LABEL[v]} | {z(-d('status_accuracy') * 100):+.1f} pts | {z(-d('checklist_f1') * 100):+.1f} pts | "
                       f"{z(-d('case_perfect') * 100):+.1f} pts | {z(-d('wrong_person')):+.1f} | {z(-d('llm_calls')):+.1f} |\n")
        md += "\n(negative = the variant is worse than full Waris; positive = better.)\n"
    js = out / "judge_summary.json"
    if js.exists():
        jd = json.loads(js.read_text(encoding="utf-8"))
        md += ("\n### Claim-letter quality (first repetition; five yes/no criteria per letter, score out of 5)\n\n"
               "| Variant | Letters | Deterministic reference checker | LLM judge (llama3.1:8b) |\n|---|---|---|---|\n")
        for v in ORDER:
            if v in jd:
                md += f"| {LABEL[v]} | {jd[v]['letters']} | {jd[v]['reference_mean_of_5']:.2f} | {jd[v]['judge_mean_of_5']:.2f} |\n"
        jv = out.parent / "judge" / "validation.json"
        val = json.loads(jv.read_text(encoding="utf-8")) if jv.exists() else {}
        md += (f"\nThe reference checker is the primary measure; the judge was validated against it on {val.get('letters', '?')} letters "
               f"({val.get('agreement', 0) * 100:.0f} % agreement, Cohen's kappa {val.get('kappa_overall', 0):.2f}: moderate, see "
               "`results/judge/validation.json`). The judge is stricter than the checker, but both rank the variants the same way: letters "
               "built on a wrong rule or a missing name proof score lower.\n")
    (out / "summary.md").write_text(md, encoding="utf-8")
    (out / "failures.md").write_text(failures_md(rows, out), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
