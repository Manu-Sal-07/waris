# Waris evaluation results

Synthetic data only. 300 runs. The family is simulated by a scripted oracle (answers from the answer key); labels come from the generator, never from an LLM.

### Held-out test split (headline numbers)

20 cases per run; repetitions per variant: [1] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 70.4% | 92.6% | 100.0% | 100.0% | 100.0% |
| Checklist F1 | 65.9% | 74.8% | 96.0% | 100.0% | 100.0% |
| Checklist precision | 69.4% | 82.5% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 62.8% | 68.4% | 92.3% | 100.0% | 100.0% |
| Asset recall | 81.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 90.0% | 95.0% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 20.0% | 40.0% | 55.0% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.6 | 2.6 | 2.5 | 0.0 | 2.5 |
| Tool calls / case | 1.3 | 1.3 | 1.3 | 1.3 | 1.3 |
| Verifier rounds / case | 0.00 | 1.45 | 1.00 | 1.45 | 1.45 |
| Seconds / case | 3.1 | 3.4 | 3.3 | 0.0 | 3.4 |

### Dev split

40 cases per run; repetitions per variant: [1] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 71.4% | 89.8% | 100.0% | 100.0% | 100.0% |
| Checklist F1 | 53.6% | 65.4% | 96.6% | 100.0% | 100.0% |
| Checklist precision | 55.0% | 73.5% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 52.2% | 59.0% | 93.4% | 100.0% | 100.0% |
| Asset recall | 85.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 11.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 87.5% | 92.5% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 12.5% | 32.5% | 65.0% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.6 | 2.6 | 2.5 | 0.0 | 2.5 |
| Tool calls / case | 1.4 | 1.4 | 1.4 | 1.4 | 1.4 |
| Verifier rounds / case | 0.00 | 1.35 | 1.00 | 1.35 | 1.35 |
| Seconds / case | 3.2 | 3.4 | 3.2 | 0.0 | 3.3 |

### All 60 cases

60 cases per run; repetitions per variant: [1] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 71.1% | 90.8% | 100.0% | 100.0% | 100.0% |
| Checklist F1 | 57.8% | 68.8% | 96.4% | 100.0% | 100.0% |
| Checklist precision | 59.8% | 76.8% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 55.9% | 62.3% | 93.0% | 100.0% | 100.0% |
| Asset recall | 84.2% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 15.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 88.3% | 93.3% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 15.0% | 35.0% | 61.7% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.6 | 2.6 | 2.5 | 0.0 | 2.5 |
| Tool calls / case | 1.4 | 1.4 | 1.4 | 1.4 | 1.4 |
| Verifier rounds / case | 0.00 | 1.38 | 1.00 | 1.38 | 1.38 |
| Seconds / case | 3.2 | 3.4 | 3.3 | 0.0 | 3.4 |

### What each component contributes (held-out test split, difference from full Waris)

| Variant | Δ status accuracy | Δ checklist F1 | Δ cases fully correct | Δ wrong-person | Δ LLM calls |
|---|---|---|---|---|---|
| One-pass baseline | -29.6 pts | -34.1 pts | -80.0 pts | +4.0 | +0.1 |
| Waris − Verifier | +0.0 pts | -4.0 pts | -45.0 pts | +0.0 | +0.0 |
| Waris − grading/re-query | -7.4 pts | -25.2 pts | -60.0 pts | +0.0 | +0.1 |
| Waris, LLM off | +0.0 pts | +0.0 pts | +0.0 pts | +0.0 | -2.5 |

(negative = the variant is worse than full Waris; positive = better.)
