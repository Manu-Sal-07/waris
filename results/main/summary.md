# Waris evaluation results

Synthetic data only. 900 runs. The family is simulated by a scripted oracle (answers from the answer key); labels come from the generator, never from an LLM.

### Held-out test split (headline numbers)

20 cases per run; repetitions per variant: [3] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 73.1% | 92.3% | 100.0% | 100.0% | 100.0% |
| Checklist F1 | 57.8% | 69.0% | 97.1% | 100.0% | 100.0% |
| Checklist precision | 59.3% | 75.6% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 56.5% | 63.6% | 94.4% | 100.0% | 100.0% |
| Asset recall | 80.8% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 4.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 85.0% | 90.0% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 20.0% | 35.0% | 70.0% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.5 | 4.2 | 4.2 | 0.0 | 4.2 |
| Tool calls / case | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 |
| Verifier rounds / case | 0.00 | 1.30 | 1.00 | 1.30 | 1.30 |
| Seconds / case | 3.5 ± 0.2 | 5.4 ± 0.4 | 5.3 ± 0.5 | 0.1 ± 0.0 | 5.5 ± 0.3 |

### Dev split

40 cases per run; repetitions per variant: [3] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 68.0% | 90.0% | 100.0% | 100.0% | 100.0% |
| Checklist F1 | 60.2% | 68.7% | 96.0% | 100.0% | 100.0% |
| Checklist precision | 65.0% | 77.4% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 56.0% | 61.7% | 92.3% | 100.0% | 100.0% |
| Asset recall | 82.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 8.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 90.0% | 95.0% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 20.0% | 35.0% | 57.5% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.5 | 4.2 | 4.1 | 0.0 | 4.1 |
| Tool calls / case | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 |
| Verifier rounds / case | 0.00 | 1.43 | 1.00 | 1.43 | 1.43 |
| Seconds / case | 3.5 ± 0.2 | 5.3 ± 0.4 | 5.3 ± 0.4 | 0.1 ± 0.0 | 5.4 ± 0.3 |

### All 60 cases

60 cases per run; repetitions per variant: [3] (mean ± standard deviation over repetitions)

| Metric | One-pass baseline | Waris − grading/re-query | Waris − Verifier | Waris, LLM off | Waris (full) |
|---|---|---|---|---|---|
| Status accuracy | 69.7% | 90.8% | 100.0% | 100.0% | 100.0% |
| Checklist F1 | 59.4% | 68.8% | 96.4% | 100.0% | 100.0% |
| Checklist precision | 63.0% | 76.8% | 100.0% | 100.0% | 100.0% |
| Checklist recall | 56.2% | 62.3% | 93.0% | 100.0% | 100.0% |
| Asset recall | 81.6% | 100.0% | 100.0% | 100.0% | 100.0% |
| Wrong-person matches | 12.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Abstention correct (cases) | 88.3% | 93.3% | 100.0% | 100.0% | 100.0% |
| Citation coverage | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Cases fully correct (status, abstention, exact checklist, no wrong person) | 20.0% | 35.0% | 61.7% | 100.0% | 100.0% |
| Family-question precision | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Family-question recall | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| LLM calls / case | 2.5 | 4.2 | 4.1 | 0.0 | 4.1 |
| Tool calls / case | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 |
| Verifier rounds / case | 0.00 | 1.38 | 1.00 | 1.38 | 1.38 |
| Seconds / case | 3.5 ± 0.2 | 5.3 ± 0.4 | 5.3 ± 0.4 | 0.1 ± 0.0 | 5.4 ± 0.3 |

### What each component contributes (held-out test split, difference from full Waris)

| Variant | Δ status accuracy | Δ checklist F1 | Δ cases fully correct | Δ wrong-person | Δ LLM calls |
|---|---|---|---|---|---|
| One-pass baseline | -26.9 pts | -42.2 pts | -80.0 pts | +4.0 | -1.7 |
| Waris − Verifier | +0.0 pts | -2.9 pts | -30.0 pts | +0.0 | +0.0 |
| Waris − grading/re-query | -7.7 pts | -31.0 pts | -65.0 pts | +0.0 | +0.1 |
| Waris, LLM off | +0.0 pts | +0.0 pts | +0.0 pts | +0.0 | -4.2 |

(negative = the variant is worse than full Waris; positive = better.)

### Claim-letter quality (first repetition; five yes/no criteria per letter, score out of 5)

| Variant | Letters | Deterministic reference checker | LLM judge (llama3.1:8b) |
|---|---|---|---|
| One-pass baseline | 74 | 3.66 | 3.54 |
| Waris − grading/re-query | 72 | 4.08 | 3.74 |
| Waris − Verifier | 68 | 4.46 | 3.94 |
| Waris, LLM off | 68 | 4.76 | 4.29 |
| Waris (full) | 68 | 4.76 | 4.16 |

The reference checker is the primary measure; the judge was validated against it on 33 letters (91 % agreement, Cohen's kappa 0.61, `results/judge/validation.json`). The judge is stricter than the checker (it over-flags the "no invented facts" criterion), but both rank the variants the same way: letters built on a wrong rule or a missing name proof score lower.
