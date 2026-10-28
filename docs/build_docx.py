"""Builds docs/Waris_Design_Document_Review2.docx (target: 5 pages, A4) from the same figures as the PPT.

Run:  python docs/build_docx.py
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
TEAL, INK, GREY = RGBColor(0x0B, 0x6E, 0x6E), RGBColor(0x1F, 0x2D, 0x3D), RGBColor(0x6B, 0x78, 0x85)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(1.7)
sec.top_margin, sec.bottom_margin = Cm(1.5), Cm(1.5)

st = doc.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(9.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after = Pt(3)
st.paragraph_format.line_spacing = 1.04


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def cell_margins(table, top=30, bottom=30, left=70, right=70):
    tblPr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    tblPr.append(m)


def H(text, size=12.5, before=7):
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(before), Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold, r.font.size, r.font.name, r.font.color.rgb = True, Pt(size), "Cambria", TEAL
    return p


def P(text="", bold_lead=None, size=None, color=None, italic=False, after=3):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        if size:
            r.font.size = Pt(size)
    r = p.add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    return p


def B(text, bold_lead=None, size=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.left_indent = Cm(0.5)
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        if size:
            r.font.size = Pt(size)
    r = p.add_run(text)
    if size:
        r.font.size = Pt(size)
    return p


def T(rows, widths, size=8.3, header=True):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    cell_margins(t)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(widths[j])
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(val)
            r.font.size = Pt(size)
            if header and i == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                shade(c, "0B6E6E")
            else:
                if j == 0:
                    r.bold = True
                if i % 2 == 1:
                    shade(c, "EAF4F4")
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return t


def FIGURE(name, width_cm, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after, p.paragraph_format.keep_with_next = Pt(0), True
    p.add_run().add_picture(str(FIG / name), width=Cm(width_cm))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(4)
    r = c.add_run(caption)
    r.italic, r.font.size, r.font.color.rgb = True, Pt(8), GREY


# ====================================================================== title
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(0)
r = p.add_run("Waris: Design and Architecture")
r.bold, r.font.size, r.font.name, r.font.color.rgb = True, Pt(20), "Cambria", TEAL
P("An agentic AI system for unclaimed inheritance recovery  ·  Review 2 Design Document", size=10.5, color=GREY, italic=True, after=3)
T([["Course", "Agentic AI (26CD7PEAAI) · B.E. CSE (Data Science) · Sem VII · BMS College of Engineering · Dr. Kalyan Nagaraj"],
   ["Team", "Srijan C Vachadmath (Team Lead) · Chirag T · Manohara Salmani · Mohammed Arshaq"],
   ["Sector / niche", "Personal finance and legal-tech: unclaimed inheritance recovery for families of deceased persons"],
   ["Patterns used", "Supervisor multi-agent (plan-and-execute) · ReAct tool use · corrective (agentic) RAG · reflection (Verifier critic loop) · human-in-the-loop · durable checkpointed workflow"]],
  [3.0, 14.6], size=8.5, header=False)

# ====================================================================== 1
H("1. Problem, decision and scope", before=2)
P("Over ₹1.1 lakh crore of financial assets lay unclaimed in India in FY26 [1], and banks returned only ₹10,297 crore between April 2022 and "
  "November 2025; the Supreme Court asked in May 2026 how legal heirs are even informed [2]. Government portals (UDGAM, Bima Bharosa, IEPF, the June 2026 "
  "Common Landing Portal) help families search, but none knows each institution's claim rules, fixes mismatches such as ‘R. Subramanian’ versus "
  "‘Ramaswamy Subramanian’, or builds the claim. Waris targets that gap with one decision:")
p = P("For each asset a deceased person left behind (bank deposit, life insurance, shares): is the claim ready to file, and if not, exactly what is missing?",
      bold_lead="Decision supported. ", after=2)
P("Output per asset is READY, MISSING_ITEMS or NEEDS_HUMAN_REVIEW with a document checklist in which every item cites the rule it came from. "
  "Waris is advisory only: it never moves money, never submits a claim and never decides legal heirship; all data is synthetic and personal details are masked in traces.",
  bold_lead="Scope and safety. ")

# ====================================================================== 2
H("2. System architecture")
FIGURE("fig1_architecture.png", 16.4, "Figure 1. Layered architecture: LangGraph orchestration over tools and data, with observability across all layers.")
T([["Component", "Technology", "Responsibility", "Owner", "Status"],
   ["Orchestration, HITL, checkpoints", "LangGraph, SqliteSaver", "graph wiring, interrupts, resume", "Srijan", "built"],
   ["Mock portals + identity matching", "FastAPI, SQLite, RapidFuzz", "noisy bank/insurer/registry records; name + DOB + city score", "Chirag", "built (OCR: Review 3)"],
   ["Rule corpus + retrieval + grading", "Markdown, Chroma", "cited claim procedures; retrieve, grade, re-query, abstain", "Manohara", "built"],
   ["Tracing, evaluation, tests", "Langfuse, JSONL/HTML, pytest", "trace every step; scorecard vs answer key; 18 tests", "Mohammed", "built (full harness: Review 3/4)"],
   ["LLM", "Llama 3.1 8B via Ollama, T=0", "choose next tool; grade borderline rules only", "all", "built, with fixed fallbacks"]],
  [3.7, 3.4, 5.6, 1.7, 3.2], size=8)

# ====================================================================== 3
H("3. Agent graph, state and data flow")
P("The system is a LangGraph state machine. A Supervisor validates input, plans one task per asset type and routes; four specialists do the work. "
  "State is checkpointed in SQLite after every node under thread_id = case_id, so a killed process resumes at the exact step. Two nodes call "
  "interrupt(): identity confirmation (on a medium match) and final release.")
FIGURE("fig2_graph.png", 16.0, "Figure 2. The compiled graph (printed from code with --show-graph). Dashed red: Verifier send-back, ≤ 6 rounds. Blue: human interrupts.")
P("case_id, deceased, claimant, plan, candidate_assets (record, match score, evidence, identity_confirmed), rejected_candidates, applicable_rules "
  "(asset → graded rules), abstained, claim_packs (status, requirements{doc_code, rule_id, have_it}, missing, notes), verifier_feedback, round, llm_calls, human_answers, done. "
  "Account numbers, PAN and phone are masked before any trace leaves the process.",
  bold_lead="CaseState (working memory) holds: ")
FIGURE("fig3_sequence.png", 15.2, "Figure 3. Meena's case end to end: Moment 1 (name variant, namesakes), Moment 2 (nominee rule graded unfit), Moment 3 (address mismatch → ask), and the Verifier feedback loop.")

# ====================================================================== 4
H("4. Agentic patterns: where, why, and what was rejected")
T([["Pattern", "Where in Waris", "Why chosen", "Alternative rejected"],
   ["Plan-and-execute", "Supervisor plans one task per asset type", "asset types known up front; plan is auditable", "pure ReAct for everything: unbounded, hard to audit"],
   ["ReAct [3]", "Tracer: LLM picks a portal, observes, picks the next", "next search depends on what came back", "fixed pipeline: cannot adapt to an empty or failed source"],
   ["Corrective / agentic RAG [4]", "Rules Expert: retrieve → grade → re-query ≤ 2 → abstain", "the most similar rule can be the wrong procedure (nominee vs legal heir)", "plain top-k RAG: wrong rule passes silently"],
   ["Reflection / critic [5]", "Verifier V1–V5, send back with a reason", "a separate critic catches omissions and can be ablated", "self-check in the Builder: biased, cannot be switched off"],
   ["Supervisor multi-agent", "Supervisor + 4 specialists", "one router holds every limit and safety rule", "peer-to-peer swarm: loops harder to bound"],
   ["Human-in-the-loop", "interrupt() on medium identity match and before release", "a wrong-person match is the worst error", "auto-accept above a threshold: breaks the 0 wrong-person target"],
   ["Durable workflow + memory", "SQLite checkpoint per node; separate case file", "cases run for weeks as documents arrive", "in-memory state: restart loses the case"]],
  [2.9, 4.5, 5.0, 5.2], size=8)
P("Status, citations, identity scores, rule metadata grading and every limit are fixed code; the LLM only chooses the next tool (validated JSON; "
  "tool arguments always come from case facts) and grades a rule when metadata cannot decide. This makes runs reproducible, testable against an answer key, "
  "and independent of a small model: if Ollama is slow, wrong or off, a deterministic fallback keeps the run going. "
  "Verifier checks: V1 every item has a rule_id; V2 that rule exists and requires that document; V3 a name variant implies name-variation proof; "
  "V4 a medium match must be family-confirmed; V5 the pack validates against the ClaimPack schema. Each failure names the agent that can fix it (V3 → Rules Expert, V1/V2/V5 → Builder, V4 → identity gate).",
  bold_lead="Fixed code versus LLM. ")
T([["Limit (all loops bounded)", "Value", "When hit"],
   ["Verifier rounds per case · same check failing twice", "6 · 2", "asset → NEEDS_HUMAN_REVIEW · asset escalated (no ping-pong)"],
   ["RAG re-queries per asset · Tracer steps · LLM calls per case", "2 · 8 · 40", "abstain ‘I don't know’ · stop searching · finalize with fixed fallbacks"],
   ["Tool timeout · retries · LLM invalid JSON", "10 s · 2 · 1 retry", "source flagged unavailable, never guessed · then fixed fallback"]],
  [7.4, 2.4, 7.8], size=8)
P("Identity policy: score = 0.5·name + 0.3·DOB + 0.2·city (a missing field counts 0.5; a DOB conflict is a namesake and is rejected outright). "
  "≥ 0.85 accept; 0.60–0.85 always ask the family; < 0.60 reject. Thresholds are tuned on the 40 dev cases only.",
  bold_lead="Agentic RAG and identity. ")

# ====================================================================== 5
H("5. Data sources and tool plan")
P("Three FastAPI portals over SQLite (/bank, /insurer, /registry) return fuzzy, noisy candidates including namesakes (same name, different DOB), initials, old addresses, "
  "and one record carrying injected instruction text to test the prompt-injection guard. Portal text is treated as data: only whitelisted fields pass on.",
  bold_lead="Mock portals. ")
P("Six markdown rule files in Chroma, written from public RBI, IRDAI and IEPF procedure types, each versioned and marked verified: illustrative until checked against "
  "official circulars. Front matter: rule_id, institution_type, topic (claim_procedure | name_variation), applies_to (nominee | legal_heir | any), amount_band, requires[DOC_*], version, source_url. "
  "Twenty fixed DOC_* codes are shared by rules, Builder and answer keys, which makes checklist precision and recall computable. "
  "One situation is deliberately uncovered (insurance claim where the nominee has died) so the abstention path is testable.",
  bold_lead="Rule corpus. ")
P("(1) generate the hidden true world (person, assets, family); (2) write messy portal records from it; (3) write partial family knowledge and scans; "
  "(4) write the answer key automatically. Labels never come from an LLM. Plan: 60 cases (15 easy, 25 medium, 20 hard), 40 dev and 20 held-out; every scenario "
  "(name variants, namesake, partial info, no assets, several accounts, nominee vs heir, amounts, joint account, missing documents, conflicting documents, missing rule, "
  "blurry/rotated scans, later-session document, injection scan) appears at least 3 times. The Meena case is hand-built to this design.",
  bold_lead="Synthetic data pipeline. ")
T([["Tool", "Input → output", "Called by", "Timeout / failure behaviour", "Status"],
   ["search_bank / insurer / registry", "name, dob?, city? → candidate records", "Tracer", "10 s, retry 2, then flagged unavailable", "built"],
   ["match_name · identity_score", "names / deceased + record → score, variant, band, evidence", "Tracer", "pure functions", "built"],
   ["retrieve_rules · grade_rule", "query, institution, topic, exclude → rule; facts + rule → fits, reason", "Rules Expert", "none left → abstain; metadata first, LLM only if undecidable", "built"],
   ["compute_status", "requirements, flags → READY / MISSING_ITEMS / NEEDS_HUMAN_REVIEW", "Finalize", "pure function", "built"],
   ["ocr_document · draft_letter", "scan → text, fields, confidence · asset, requirements → letter", "Tracer · Builder", "confidence < 0.6 → ask human · template + LLM", "Review 3"]],
  [3.5, 5.6, 2.0, 4.9, 1.6], size=8)

# ====================================================================== 6
H("6. Evaluation and experiment plan")
T([["Metric", "Definition", "Target"],
   ["Asset recall", "true assets found / true assets", "high"],
   ["Wrong-person matches", "claimed assets that are namesakes or not true assets", "0 (hard gate)"],
   ["Status accuracy · abstention correctness", "assets with the key's status / assets · NEEDS_HUMAN_REVIEW exactly where the key says", "high"],
   ["Checklist precision / recall / F1", "micro-averaged over DOC_* codes versus the answer key", "high"],
   ["Citation coverage", "requirements with a rule_id that exists in the corpus / all requirements", "100 %"],
   ["Letter quality", "LLM judge with a rubric (correct asset and claimant, documents listed, formal, no invented facts); checked against our own marks on 15 letters, κ ≥ 0.6", "agrees with humans"],
   ["Cost and process", "LLM calls, tool calls, rounds, wall time; re-query rate; share of send-backs that led to a fix; HITL trigger rate and whether warranted", "within caps"]],
  [4.4, 10.6, 2.6], size=8)
P("H1: full Waris beats a one-pass baseline (single retrieval + single LLM call, no grading, re-query, Verifier or HITL) on checklist F1 and abstention correctness. "
  "H2: removing the Verifier lowers recall of the name-variation proof. H3: removing grading and re-query lowers status accuracy on nominee-vs-heir cases. "
  "Each variant runs 3 times (different seeds and temperatures); we report mean ± spread, and a decision rule fixed in advance: keep a component if it adds the agreed gain for the extra calls it costs. "
  "Failures are reported with trace screenshots. Final numbers come from the 20 held-out cases; all 60 are reported separately.",
  bold_lead="Experiment. ")

# ====================================================================== 7
H("7. Current build status and evidence")
FIGURE("fig5_demo_excerpt.png", 16.4, "Figure 4. Excerpt of a real run (python -m waris.run --case meena) showing the behaviours above.")
P("The harness already scores a run against the answer key; on Meena's case: asset recall 100 %, wrong-person matches 0, status accuracy 100 %, checklist precision/recall 100 %, "
  "citation coverage 100 %, abstention correct. This is one hand-built case, so it shows that the harness and the system work end to end; it is not a result. "
  "18 automated tests pass (identity, grading, Verifier checks, status, limits, guardrails, schema, portal failure, end-to-end graph, memory). "
  "A killed process resumes from its checkpoint, and a second run reuses the family's earlier answer from the case file instead of asking again.",
  bold_lead="Evidence. ")
P("OCR of scans and claim-letter drafting; Streamlit approval screen; seeded 60-case generator and full eval harness; LLM-judge validation; A/B and ablation runs; "
  "verification of rule details against official sources.", bold_lead="Not yet built (Review 3/4). ")
P("Small local model reliability (mitigated: the run never depends on it); OCR on faded scans (we generate scans, so difficulty is controlled); rule accuracy "
  "(labelled illustrative; Waris gives no legal advice); wrong-person matches (hard gate, ask-on-medium policy).", bold_lead="Risks. ")

H("References", size=10.5, before=4)
for ref in ["[1] Lapaas Voice, “Unclaimed assets cross ₹1.1 lakh crore in FY26”, citing government data to the Lok Sabha.",
            "[2] Moneylife, “Supreme Court seeks response on informing heirs of unclaimed assets”, 6 May 2026.",
            "[3] S. Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models”, ICLR 2023.",
            "[4] S.-Q. Yan et al., “Corrective Retrieval Augmented Generation”, 2024.",
            "[5] N. Shinn et al., “Reflexion: Language Agents with Verbal Reinforcement Learning”, NeurIPS 2023.",
            "[6] LangGraph, Langfuse, Chroma, Ollama and RapidFuzz open-source documentation (tools used)."]:
    P(ref, size=8, after=0)

out = HERE / "Waris_Design_Document_Review2.docx"
doc.save(out)
print("saved", out)
