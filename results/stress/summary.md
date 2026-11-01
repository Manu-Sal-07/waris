# Waris evaluation results

Synthetic data only. 60 runs. The family is simulated by a scripted oracle (answers from the answer key); labels come from the generator, never from an LLM.

### Held-out test split (headline numbers)

8 cases per run; repetitions per variant: [1] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 75.0% | 100.0% | 0.0% | 100.0% | 100.0% |
| Checklist F1 | 58.0% | 72.7% | 89.7% | 100.0% | 100.0% |
| Checklist precision | 76.9% | 82.4% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 46.5% | 65.1% | 81.4% | 100.0% | 100.0% |
| Asset recall | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 0.0% | 25.0% | 0.0% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.0 | 2.0 | 2.0 | 0.0 | 2.0 |
| Tool calls / case | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Verifier rounds / case | 0.00 | 2.00 | 1.00 | 2.00 | 2.00 |
| Seconds / case | 2.4 | 2.6 | 2.6 | 0.0 | 2.9 |

### Dev split

4 cases per run; repetitions per variant: [1] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 50.0% | 100.0% | 0.0% | 100.0% | 100.0% |
| Checklist F1 | 64.7% | 78.9% | 89.5% | 100.0% | 100.0% |
| Checklist precision | 84.6% | 88.2% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 52.4% | 71.4% | 81.0% | 100.0% | 100.0% |
| Asset recall | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 0.0% | 50.0% | 0.0% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.0 | 2.0 | 2.0 | 0.0 | 2.0 |
| Tool calls / case | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Verifier rounds / case | 0.00 | 2.00 | 1.00 | 2.00 | 2.00 |
| Seconds / case | 2.3 | 2.5 | 2.5 | 0.0 | 2.5 |

### All 60 cases

12 cases per run; repetitions per variant: [1] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 66.7% | 100.0% | 0.0% | 100.0% | 100.0% |
| Checklist F1 | 60.2% | 74.8% | 89.7% | 100.0% | 100.0% |
| Checklist precision | 79.5% | 84.3% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 48.4% | 67.2% | 81.2% | 100.0% | 100.0% |
| Asset recall | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 0.0% | 33.3% | 0.0% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.0 | 2.0 | 2.0 | 0.0 | 2.0 |
| Tool calls / case | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Verifier rounds / case | 0.00 | 2.00 | 1.00 | 2.00 | 2.00 |
| Seconds / case | 2.3 | 2.6 | 2.6 | 0.0 | 2.8 |

### What each component contributes (held-out test split, difference from full Waris)

| Variant | Δ status accuracy | Δ checklist F1 | Δ cases fully correct | Δ wrong-person | Δ LLM calls |
|---|---|---|---|---|---|
| One-pass baseline | -25.0 pts | -42.0 pts | -100.0 pts | +0.0 | +0.0 |
| Waris − Verifier | -100.0 pts | -10.3 pts | -100.0 pts | +0.0 | +0.0 |
| Waris − grading/re-query | +0.0 pts | -27.3 pts | -75.0 pts | +0.0 | +0.0 |
| Waris, LLM off | +0.0 pts | +0.0 pts | +0.0 pts | +0.0 | -2.0 |

(negative = the variant is worse than full Waris; positive = better.)
