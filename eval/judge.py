"""LLM-as-judge for claim letters, and its validation.

    python -m eval.judge validate                   # check the judge against reference marks (writes results/judge/)
    python -m eval.judge score results/main         # judge every saved letter of an evaluation run
    python -m eval.judge agree results/judge/human_marks.csv   # agreement with the team's own marks (once filled in)

The judge model is WARIS_JUDGE_MODEL (default llama3.1:8b; llama3.2 and gemma4:26b were tried and were worse, see the
validation notes). Disclosure: this is the same model that writes the letters' opening paragraph, so the judge is never trusted
on its own: it is validated against a deterministic reference checker and the checker's numbers are reported next to it.
It sees the REFERENCE FACTS (from the answer key) and the letter, and marks five yes/no criteria:
   asset_claimant  the letter names the right deceased, claimant and kind of asset
   documents       the enclosed / still-to-follow lists match the true checklist (a letter built on the wrong rule fails)
   formal          formal, polite tone (no slang, no exclamation marks)
   no_invented     no amounts, dates, promises or facts that were not supplied
   clear_request   it asks the institution for something concrete (acknowledge / guide)
Reference marks come from a deterministic checker over the same facts. The judge is trusted only if it agrees with them
(Cohen's kappa); the same CSV layout is used for the team's own marks so agreement with people can be computed too.
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

from waris import config, llm
from waris.doc_codes import DOC_CODES

CRITERIA = ["asset_claimant", "documents", "formal", "no_invented", "clear_request"]
_DESC2CODE = {v: k for k, v in DOC_CODES.items()}
_KIND = {"bank_deposit": ("deposit", "account", "savings"), "life_insurance": ("policy", "insurance"), "shares": ("share",)}
_FORBID = re.compile(r"guarantee|assure|promise|compensation|interest|penalt|urgent|immediately|\bRs\.?\s*\d|₹|\d+\s*lakh|"
                     r"matur|entitled|proceeds|balance|payable|credited", re.I)
_INFORMAL = re.compile(r"!|\bhey\b|\bguys\b|\bthanks a lot\b|\bASAP\b|\bplease hurry\b", re.I)


# ------------------------------------------------------------------ facts + reference marks
def facts_for(case: dict, key: dict, record_id: str) -> dict | None:
    """Reference facts for one letter: what a correct letter must say. None when the record is not a true asset."""
    a = next((x for x in key["assets"] if x["record_id"] == record_id), None)
    if a is None:
        return None
    return {"deceased": case["deceased"]["name"], "claimant": case["claimant"]["name"], "asset_type": a["asset_type"],
            "enclosed": [d for d in a["required_docs"] if d not in a["missing"]], "to_follow": list(a["missing"]),
            "dod": case["deceased"].get("dod") or ""}


def _section(text: str, head: str) -> set[str]:
    m = re.search(re.escape(head) + r"\n((?:  \d+\. .*\n?)+)", text + "\n")
    if not m:
        return set()
    return {_DESC2CODE.get(re.sub(r"^\s*\d+\.\s*", "", ln).strip()) for ln in m.group(1).splitlines()} - {None}


def reference_marks(letter: str, facts: dict | None) -> dict[str, int]:
    if facts is None:                                    # a letter about something that is not the family's asset
        return {c: 0 for c in CRITERIA} | {"formal": int(not _INFORMAL.search(letter)), "clear_request": int("request" in letter.lower() or "kindly" in letter.lower())}
    low = letter.lower()
    ok_asset = (facts["deceased"].lower() in low and facts["claimant"].lower() in low
                and any(k in low for k in _KIND[facts["asset_type"]]))
    enc = _section(letter, "Documents enclosed with this letter:")
    fol = _section(letter, "Documents I will submit shortly:")
    ok_docs = enc == set(facts["enclosed"]) and fol == set(facts["to_follow"])
    allowed_nums = set(re.findall(r"\d+", facts["dod"])) | set(re.findall(r"\*+(\d+)", letter))     # date of death + the masked reference
    body = re.sub(r"\n  \d+\. ", "\n  ", letter)                              # list numbering is not a fact
    nums = set(re.findall(r"\d+", re.sub(r"\*+\d+", "", body)))
    dates_ok = all(d == facts["dod"] and re.search(r"passed away|died|death|demise", body[max(0, m.start() - 40):m.start()], re.I)
                   for m in re.finditer(r"\d{4}-\d{2}-\d{2}", body) for d in [m.group(0)])
    ok_noinvent = not _FORBID.search(letter) and nums <= allowed_nums and dates_ok
    return {"asset_claimant": int(ok_asset), "documents": int(ok_docs), "formal": int(not _INFORMAL.search(letter) and "Yours faithfully" in letter),
            "no_invented": int(ok_noinvent), "clear_request": int("request" in low or "kindly" in low)}


# ------------------------------------------------------------------ the LLM judge
# One narrow yes/no question per criterion (small models are unreliable at five-way holistic grading: kappa 0.24 for
# llama3.2 holistic vs 0.63 per criterion with llama3.1:8b on the validation set, see results/judge/).
_Q = {
    "asset_claimant": "Does the letter name BOTH the deceased '{deceased}' AND the claimant '{claimant}', and is it about a {kind}?",
    "documents": ("The letter must list as ENCLOSED exactly these documents: {enc}; and as TO FOLLOW exactly these: {fol}. "
                  "Compare with the two lists in the letter. Do both lists contain exactly those documents, nothing missing and nothing extra?"),
    "formal": "Is the letter written in a formal, polite style, with no slang and no exclamation marks?",
    "no_invented": ("Does the letter contain NO money amount, NO number of days, NO guarantee or promise of payment, and NO claim "
                    "that the asset matured or that the claimant is entitled to the money?"),
    "clear_request": "Does the letter ask the institution to acknowledge, guide or process something?",
}
_SYSTEM = 'You check a letter. Answer ONLY with JSON: {"answer": "yes"} or {"answer": "no"}.'
_KIND = {"bank_deposit": "bank deposit", "life_insurance": "life insurance policy", "shares": "shareholding"}


def judge_letter(letter: str, facts: dict | None) -> dict[str, int] | None:
    """Five narrow yes/no questions, each answered by the judge model. A letter about something that is not the family's
    asset is marked 0 on asset and documents without asking (the reference facts say it is wrong)."""
    marks = {}
    for c in CRITERIA:
        if facts is None and c in ("asset_claimant", "documents"):
            marks[c] = 0
            continue
        q = _Q[c].format(deceased=facts["deceased"] if facts else "", claimant=facts["claimant"] if facts else "",
                         kind=_KIND.get(facts["asset_type"], "") if facts else "",
                         enc=[DOC_CODES[d] for d in facts["enclosed"]] if facts else [],
                         fol=[DOC_CODES[d] for d in facts["to_follow"]] if facts else [])
        raw, _, _ = llm.chat_json(_SYSTEM, f"{q}\n\nLETTER:\n{letter}", model=config.JUDGE_MODEL, quiet=True)
        if not isinstance(raw, dict):
            return None
        marks[c] = int(str(raw.get("answer", "")).strip().lower().startswith("y"))
    return marks


def kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa1, pb1 = sum(a) / n, sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


# ------------------------------------------------------------------ validation set
def _perturb(text: str, kind: str, facts: dict, rng: random.Random) -> str:
    if kind == "drop_doc":                                # silently loses a required document line
        lines = text.split("\n")
        idx = [i for i, l in enumerate(lines) if re.match(r"  \d+\. ", l)]
        if idx:
            del lines[rng.choice(idx)]
        return "\n".join(lines)
    if kind == "wrong_name":
        return text.replace(facts["claimant"], "Rohan Mehta")
    if kind == "invent":
        return text.replace("Kindly acknowledge", "The bank has assured a payment of Rs 5,00,000 within 7 days. Kindly acknowledge")
    if kind == "invent_date":
        return text.replace("I am writing to start", "The deposit matured on 2017-07-01 and I am entitled to the proceeds. I am writing to start", 1)
    if kind == "informal":
        return text.replace("Dear Sir/Madam,", "Hey guys!!").replace("Yours faithfully", "Thanks a lot!")
    return text


def build_validation_set(limit_genuine: int = 12) -> list[dict]:
    """Genuine letters produced by Waris's own run + deliberately damaged copies (so both marks occur)."""
    from waris.agents.letters import render, template_paragraph
    rng = random.Random(7)
    sp = json.loads((config.CASES_DIR / "split.json").read_text(encoding="utf-8"))
    out = []
    for cid in sorted(sp["dev"] + sp["test"]):
        if len(out) >= limit_genuine:
            break
        case = json.loads((config.CASES_DIR / cid / "input.json").read_text(encoding="utf-8"))
        key = json.loads((config.CASES_DIR / cid / "answer_key.json").read_text(encoding="utf-8"))
        for a in key["assets"]:
            if a["status"] == "NEEDS_HUMAN_REVIEW" or len(out) >= limit_genuine:
                continue
            facts = facts_for(case, key, a["record_id"])
            f = {"deceased": facts["deceased"], "dod": facts["dod"], "claimant": facts["claimant"],
                 "relationship": case["claimant"]["relationship"], "claimant_type": case["claimant"]["claimant_type"],
                 "product": {"bank_deposit": "deposit", "life_insurance": "policy", "shares": "shares"}[a["asset_type"]],
                 "holder": facts["deceased"], "ref": "", "inst": {"bank_deposit": "bank", "life_insurance": "insurer", "shares": "registry"}[a["asset_type"]],
                 "enclosed": facts["enclosed"], "to_follow": facts["to_follow"]}
            out.append({"id": f"{cid}-{a['record_id']}-genuine", "letter": render(f, template_paragraph(f)), "facts": facts, "kind": "genuine"})
    genuine = list(out)
    for kind in ("drop_doc", "wrong_name", "invent", "invent_date", "informal"):
        for g in genuine[:5] if kind not in ("informal", "invent_date") else genuine[:3]:
            out.append({"id": g["id"].replace("genuine", kind), "letter": _perturb(g["letter"], kind, g["facts"], rng),
                        "facts": g["facts"], "kind": kind})
    return out


def validate(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    items = build_validation_set()
    llm.set_enabled(True)
    rows, ref_all, judge_all = [], [], []
    per = {c: ([], []) for c in CRITERIA}
    for it in items:
        ref = reference_marks(it["letter"], it["facts"])
        j = judge_letter(it["letter"], it["facts"]) or {c: 0 for c in CRITERIA}
        rows.append({"id": it["id"], "kind": it["kind"], **{f"ref_{c}": ref[c] for c in CRITERIA}, **{f"judge_{c}": j[c] for c in CRITERIA}})
        for c in CRITERIA:
            per[c][0].append(ref[c])
            per[c][1].append(j[c])
            ref_all.append(ref[c])
            judge_all.append(j[c])
    res = {"letters": len(items), "judge_model": config.JUDGE_MODEL,
           "agreement": sum(x == y for x, y in zip(ref_all, judge_all)) / len(ref_all), "kappa_overall": kappa(ref_all, judge_all),
           "kappa_by_criterion": {c: kappa(*per[c]) for c in CRITERIA},
           "agreement_by_criterion": {c: sum(x == y for x, y in zip(*per[c])) / len(per[c][0]) for c in CRITERIA}}
    with (out_dir / "validation_marks.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out_dir / "validation.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    # template for the team's own marks (15 letters): fill the five columns with 1/0 and run `agree`
    pick = random.Random(11).sample(items, min(15, len(items)))
    with (out_dir / "human_marks_template.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "letter"] + CRITERIA)
        for it in pick:
            w.writerow([it["id"], it["letter"].replace("\n", " ⏎ ")] + [""] * len(CRITERIA))
    (out_dir / "validation_letters.json").write_text(json.dumps({i["id"]: i for i in items}, indent=1), encoding="utf-8")
    return res


def agree(csv_path: Path) -> dict:
    """Agreement of the judge and of the reference checker with the team's own marks."""
    items = json.loads((csv_path.parent / "validation_letters.json").read_text(encoding="utf-8"))
    human, judge, ref = [], [], []
    for row in csv.DictReader(csv_path.open(encoding="utf-8")):
        if not all(row[c].strip() in ("0", "1") for c in CRITERIA):
            continue
        it = items[row["id"]]
        j = judge_letter(it["letter"], it["facts"]) or {c: 0 for c in CRITERIA}
        r = reference_marks(it["letter"], it["facts"])
        for c in CRITERIA:
            human.append(int(row[c]))
            judge.append(j[c])
            ref.append(r[c])
    return {"marks": len(human) // len(CRITERIA), "kappa_judge_vs_human": kappa(human, judge), "kappa_reference_vs_human": kappa(human, ref)}


def score_run(run_dir: Path) -> dict:
    """Judge every saved letter of an evaluation run. -> per-variant mean score out of 5 (+ per-criterion rates)."""
    llm.set_enabled(True)
    rows = []
    for vdir in sorted((run_dir / "letters").glob("*")):
        for cdir in sorted(vdir.glob("*")):
            cid = cdir.name
            case = json.loads((config.CASES_DIR / cid / "input.json").read_text(encoding="utf-8"))
            key = json.loads((config.CASES_DIR / cid / "answer_key.json").read_text(encoding="utf-8"))
            for f in sorted(cdir.glob("*.txt")):
                rid = f.stem.split("_")[-1]
                letter = f.read_text(encoding="utf-8")
                facts = facts_for(case, key, rid)
                j = judge_letter(letter, facts) or {c: 0 for c in CRITERIA}
                ref = reference_marks(letter, facts)
                rows.append({"variant": vdir.name, "case_id": cid, "record_id": rid, "judge_total": sum(j.values()),
                             "ref_total": sum(ref.values()), **{f"judge_{c}": j[c] for c in CRITERIA}, **{f"ref_{c}": ref[c] for c in CRITERIA}})
    if not rows:
        return {}
    with (run_dir / "judge_scores.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {}
    for v in sorted({r["variant"] for r in rows}):
        sel = [r for r in rows if r["variant"] == v]
        summary[v] = {"letters": len(sel), "judge_mean_of_5": sum(r["judge_total"] for r in sel) / len(sel),
                      "reference_mean_of_5": sum(r["ref_total"] for r in sel) / len(sel),
                      **{f"judge_{c}": sum(r[f"judge_{c}"] for r in sel) / len(sel) for c in CRITERIA}}
    (run_dir / "judge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    a = argv or sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == "validate":
        print(json.dumps(validate(config.ROOT / "results" / "judge"), indent=2))
    elif a[0] == "score":
        print(json.dumps(score_run(Path(a[1])), indent=2))
    elif a[0] == "agree":
        print(json.dumps(agree(Path(a[1])), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
