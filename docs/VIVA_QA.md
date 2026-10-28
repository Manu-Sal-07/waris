# Viva Q&A: every member should be able to answer all of these

**Why is this agentic and not one prompt?** Many sources, institution-specific rules, mismatches to fix, identity to confirm, and a decision on when to stop. Each step depends on what the previous tool returned (portal results change which rule is needed; the Verifier changes the next step).

**Why is status computed by code and not the LLM?** Reproducible, testable against the answer key, and a small model invents statuses. The LLM only chooses the next tool and grades a rule when metadata cannot decide.

**What if the LLM is slow, wrong or off?** Output is validated (pydantic); one retry; then a fixed fallback order. We saw a real cold-start timeout and the run still finished correctly. `--no-llm` runs the whole case.

**What stops it looping forever?** Verifier rounds ≤ 6, same failure twice escalates the asset, RAG re-queries ≤ 2 (and the rejected rule is excluded so each re-query makes progress), Tracer steps ≤ 8, LLM calls ≤ 40, tool timeout 10 s. Hitting a limit gives NEEDS_HUMAN_REVIEW.

**How do you avoid claiming a stranger's money?** Identity score 0.5·name + 0.3·DOB + 0.2·city; a DOB conflict rejects outright (namesake); 0.60–0.85 always asks the family via interrupt; target is 0 wrong-person matches, measured.

**What does the Verifier check, and who fixes failures?** V1 cited, V2 rule exists and requires that document, V3 name variant needs name proof, V4 medium match confirmed, V5 schema. V3 goes to Rules Expert, V1/V2/V5 to Builder, V4 to the identity gate.

**Why a separate Verifier, not a self-check?** It can be removed for the ablation (H2) and it is unbiased by the Builder's own output.

**What is corrective RAG here?** Retrieve → grade fit against the claimant (not similarity) → refine and re-query → abstain. The nominee rule is the most similar chunk but wrong for a legal heir.

**What happens on restart mid-interrupt?** SqliteSaver holds the paused state (thread_id = case_id); rerunning resumes at that node. Demonstrated with `--exit-at-pause`.

**Short-term vs long-term memory?** Short-term = graph state (checkpointed). Long-term = case-file table of family answers and past results, which survives a brand-new run.

**How is prompt injection handled?** Only whitelisted fields from portal records reach the pipeline; instruction-like text is flagged and dropped; the LLM never supplies tool arguments. A portal record with "ignore the rules" is in the demo data.

**Why synthetic data?** Real inheritance data is sensitive; synthetic data has exact ground truth. Labels come from the generator, never an LLM.

**Are the rules real?** They follow public RBI/IRDAI/IEPF procedure types, are cited, and are marked `verified: illustrative` until checked. Waris gives no legal advice.

**What is the difference from UDGAM / the Common Landing Portal?** They search; Waris builds the claim.

**What is built vs planned?** Built: graph, 3 portals, 6 rules, identity policy, RAG grading, Verifier, interrupts, checkpoint/memory, guardrails, tracing, scorecard, 18 tests. Planned: OCR, letters, Streamlit, 60-case generator and full eval, judge validation, A/B and ablations.

**What does the scorecard prove?** Only that the harness and the system work end to end on one case. It is not a result; real numbers come from the held-out cases.
