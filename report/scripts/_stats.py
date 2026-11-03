import json, collections
R = [json.loads(l) for l in open("results/main/runs.jsonl", encoding="utf-8")]
for v in ["baseline", "no_grading", "no_verifier"]:
    rs = [r for r in R if r["variant"] == v and r["rep"] == 0]
    fn = sum(r["true"] - r["tp"] for r in rs)
    fp = sum(r["pred"] - r["tp"] for r in rs)
    wrong_cases = [r["case_id"] for r in rs if r["status_accuracy"] < 1]
    bad = collections.Counter()
    for r in rs:
        for rid, (got, want) in r["detail"]["bad_status"].items():
            bad[(want, got)] += 1
    print(v, "FN", fn, "FP", fp, "cases w/ wrong status", len(wrong_cases), dict(bad))
    missed = collections.Counter()
    for r in rs:
        if r["n_truth"] > r["n_found"]:
            for t in r["tags"]:
                missed[t] += r["n_truth"] - r["n_found"]
    print("  missed assets", sum(r["n_truth"] - r["n_found"] for r in rs), "wrong-person", sum(r["wrong_person_matches"] for r in rs),
          "q recall<1 cases", sum(1 for r in rs if r["question_recall"] < 1))
    print("  missed tags", dict(missed.most_common(8)))
    wp = collections.Counter(t for r in rs if r["wrong_person_matches"] for t in r["tags"])
    print("  wrong-person tags", dict(wp.most_common(8)))
# no_grading wrong statuses by tag, no_verifier f1 loss by tag
ng = [r for r in R if r["variant"] == "no_grading" and r["rep"] == 0 and r["status_accuracy"] < 1]
print("no_grading wrong-status case tags", collections.Counter(t for r in ng for t in r["tags"] if t.startswith("claimant") or t in ("no_rule", "joint_account", "amount_large")))
nv = [r for r in R if r["variant"] == "no_verifier" and r["rep"] == 0 and r["tp"] < r["true"]]
print("no_verifier cases missing docs", len(nv), "tags", collections.Counter(t for r in nv for t in r["tags"] if t.startswith("name")))
