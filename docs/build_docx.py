"""Builds docs/Waris_Design_Document_Review2.docx (A4, target 5 pages) from the same figures as the PPT.

Run:  python docs/build_docx.py
Structure: real Word heading styles (navigable), numbered tables and figures with captions, bulleted content,
running header and "Page X of Y" footer.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
TEAL, INK, GREY = RGBColor(0x0B, 0x6E, 0x6E), RGBColor(0x1F, 0x2D, 0x3D), RGBColor(0x5F, 0x6B, 0x77)
BODY_FONT, HEAD_FONT = "Calibri", "Cambria"
BODY_PT = 9.2

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.0)
sec.top_margin, sec.bottom_margin = Cm(1.6), Cm(1.4)
sec.header_distance, sec.footer_distance = Cm(0.9), Cm(0.8)
TEXT_W = 17.0  # cm


# ---------------------------------------------------------------- styles
def set_font(style, name, size, bold=None, color=None, italic=None):
    style.font.name, style.font.size = name, Pt(size)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color


def bottom_border(paragraph, color="0B6E6E", sz=6):
    pPr = paragraph._p.get_or_add_pPr()
    pb = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), color)
    pb.append(b)
    pPr.append(pb)


normal = doc.styles["Normal"]
set_font(normal, BODY_FONT, BODY_PT, color=INK)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.08

h1 = doc.styles["Heading 1"]
set_font(h1, HEAD_FONT, 13.5, bold=True, color=TEAL)
h1.paragraph_format.space_before, h1.paragraph_format.space_after = Pt(8), Pt(3)
h1.paragraph_format.keep_with_next = True

h2 = doc.styles["Heading 2"]
set_font(h2, HEAD_FONT, 11, bold=True, color=INK)
h2.paragraph_format.space_before, h2.paragraph_format.space_after = Pt(5), Pt(2)
h2.paragraph_format.keep_with_next = True

lb = doc.styles["List Bullet"]
set_font(lb, BODY_FONT, BODY_PT, color=INK)
lb.paragraph_format.space_after = Pt(2)
lb.paragraph_format.line_spacing = 1.05

lb2 = doc.styles["List Bullet 2"]
set_font(lb2, BODY_FONT, BODY_PT, color=INK)
lb2.paragraph_format.space_after = Pt(1)
lb2.paragraph_format.line_spacing = 1.05

ln = doc.styles["List Number"]
set_font(ln, BODY_FONT, BODY_PT, color=INK)
ln.paragraph_format.space_after = Pt(2)

cap = doc.styles["Caption"]
set_font(cap, BODY_FONT, 8.5, bold=False, italic=True, color=GREY)
cap.paragraph_format.space_before, cap.paragraph_format.space_after = Pt(2), Pt(8)


# ---------------------------------------------------------------- low-level helpers
def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def table_borders(table, color="B8C4CC", inner=True):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right") + (("insideH", "insideV") if inner else ()):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        borders.append(e)
    tblPr.append(borders)


def cell_margins(table, top=45, bottom=45, left=90, right=90):
    tblPr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    tblPr.append(m)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def no_split(row):
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:cantSplit")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def add_field(paragraph, instr, size=8.5, color=GREY):
    r = paragraph.add_run()
    r.font.size, r.font.color.rgb = Pt(size), color
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._r.append(fc)
        elif text == instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            r._r.append(it)
        else:
            t = OxmlElement("w:t")
            t.text = text
            r._r.append(t)


# ---------------------------------------------------------------- content helpers
_counters = {"table": 0, "figure": 0}


def H1(text):
    return doc.add_heading(text, level=1)


def H2(text):
    return doc.add_heading(text, level=2)


def P(text="", lead=None, size=None, color=None, italic=False, after=None, align=None):
    p = doc.add_paragraph()
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if align:
        p.alignment = align
    if lead:
        r = p.add_run(lead)
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


def B(text, lead=None, style="List Bullet"):
    p = doc.add_paragraph(style=style)
    if lead:
        r = p.add_run(lead)
        r.bold = True
    p.add_run(text)
    return p


def BL(lead, points):
    """A bullet with a bold lead and its first point on the same line; further points are sub-bullets."""
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(0 if len(points) > 1 else 2)
    p.paragraph_format.keep_with_next = len(points) > 1
    p.add_run(lead + ": ").bold = True
    p.add_run(points[0])
    for i, t in enumerate(points[1:]):
        q = doc.add_paragraph(style="List Bullet 2")
        q.add_run(t)
        q.paragraph_format.keep_with_next = i < len(points) - 2
    return p


def N(text, lead=None):
    return B(text, lead, style="List Number")


def CAPTION(kind, text):
    _counters[kind] += 1
    label = "Table" if kind == "table" else "Figure"
    p = doc.add_paragraph(style="Caption")
    r = p.add_run(f"{label} {_counters[kind]}. ")
    r.bold, r.italic = True, False
    r.font.color.rgb = INK
    p.add_run(text)
    return p


def TABLE(caption, rows, widths, size=8.2, first_col_bold=True):
    """Caption above, header row repeated, zebra rows, rows never split across pages."""
    cp = CAPTION("table", caption)
    cp.paragraph_format.keep_with_next = True
    cp.paragraph_format.space_after = Pt(3)
    cp.paragraph_format.space_before = Pt(5)
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    table_borders(t)
    cell_margins(t)
    for i, row in enumerate(rows):
        no_split(t.rows[i])
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(widths[j])
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.keep_with_next = i < min(2, len(rows) - 1) or len(rows) <= 5   # short tables stay whole; long ones may break (header repeats)
            r = p.add_run(val)
            r.font.size = Pt(size)
            if i == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                shade(c, "0B6E6E")
            else:
                if j == 0 and first_col_bold:
                    r.bold = True
                if i % 2 == 0:
                    shade(c, "EEF5F5")
    repeat_header(t.rows[0])
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(2)
    sp.paragraph_format.line_spacing = 0.6
    return t


def CALLOUT(lead, text):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    table_borders(t, color="0B6E6E", inner=False)
    cell_margins(t, top=70, bottom=70, left=140, right=140)
    c = t.cell(0, 0)
    c.width = Cm(TEXT_W)
    shade(c, "E3F1F1")
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(lead)
    r.bold, r.font.color.rgb = True, TEAL
    p.add_run(text)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(2)
    sp.paragraph_format.line_spacing = 0.6


def FIGURE(name, width_cm, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / name), width=Cm(width_cm))
    c = CAPTION("figure", caption)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ---------------------------------------------------------------- header / footer
hp = sec.header.paragraphs[0]
hp.text = ""
r = hp.add_run("Waris: Design and Architecture  ·  Agentic AI (26CD7PEAAI)  ·  Review 2")
r.font.size, r.font.color.rgb = Pt(8.5), GREY
bottom_border(hp, color="B8C4CC", sz=4)

fp = sec.footer.paragraphs[0]
fp.text = ""
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run("BMS College of Engineering  ·  Team: Srijan C Vachadmath, Chirag T, Manohara Salmani, Mohammed Arshaq  ·  Page ")
r.font.size, r.font.color.rgb = Pt(8.5), GREY
add_field(fp, "PAGE")
r = fp.add_run(" of ")
r.font.size, r.font.color.rgb = Pt(8.5), GREY
add_field(fp, "NUMPAGES")

# ====================================================================== title block
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(0)
r = p.add_run("Waris: Design and Architecture")
r.bold, r.font.size, r.font.name, r.font.color.rgb = True, Pt(24), HEAD_FONT, TEAL
p = P("An agentic AI system for unclaimed inheritance recovery  ·  Review 2 Design Document",
      size=11.5, color=GREY, italic=True, after=5)
bottom_border(p, sz=8)

info = doc.add_table(rows=4, cols=2)
info.alignment = WD_TABLE_ALIGNMENT.CENTER
info.autofit = False
table_borders(info)
cell_margins(info)
for i, (k, v) in enumerate([
    ("Course", "Agentic AI (26CD7PEAAI) · B.E. CSE (Data Science), Semester VII · BMS College of Engineering · Dr. Kalyan Nagaraj"),
    ("Team", "Srijan C Vachadmath (Team Lead) · Chirag T · Manohara Salmani · Mohammed Arshaq"),
    ("Sector / niche", "Personal finance and legal-tech: unclaimed inheritance recovery for families of deceased persons"),
    ("Patterns used", "Supervisor multi-agent (plan-and-execute) · ReAct tool use · corrective (agentic) RAG · reflection (Verifier critic loop) · "
                      "human-in-the-loop · durable checkpointed workflow"),
]):
    a, b = info.cell(i, 0), info.cell(i, 1)
    a.width, b.width = Cm(3.2), Cm(TEXT_W - 3.2)
    shade(a, "E3F1F1")
    for c, txt, bold in ((a, k, True), (b, v, False)):
        c.text = ""
        pp = c.paragraphs[0]
        pp.paragraph_format.space_after = Pt(0)
        rr = pp.add_run(txt)
        rr.font.size, rr.bold = Pt(9), bold
sp = doc.add_paragraph()
sp.paragraph_format.space_after = Pt(0)

# ====================================================================== 1
H1("1. Problem, decision and scope")
BL("The problem", ["Over ₹1.1 lakh crore of financial assets lay unclaimed in India in FY26 [1].",
                   "Banks returned only ₹10,297 crore between April 2022 and November 2025.",
                   "In May 2026 the Supreme Court asked how legal heirs are informed [2]."])
BL("The gap", ["Government portals (UDGAM, Bima Bharosa, IEPF) help families search.",
               "None knows each institution's claim rules or builds the claim.",
               "None resolves name mismatches such as ‘R. Subramanian’ versus ‘Ramaswamy Subramanian’."])
CALLOUT("Decision supported:  ",
        "for each asset a deceased person left behind (bank deposit, life insurance, shares), is the claim ready to file, and if not, exactly what is missing?")
BL("Output and scope", ["Per asset READY, MISSING_ITEMS or NEEDS_HUMAN_REVIEW; each checklist item cites its rule.",
                       "Advisory only: never moves money, files a claim or decides legal heirship.",
                       "All data is synthetic; personal details are masked."])

# ====================================================================== 2
H1("2. System architecture")
B("LangGraph orchestration drives five agents (Supervisor, Tracer, Rules Expert, Builder, Verifier).")
B("The agents use tools over mock institution portals and a rule knowledge base; tracing and evaluation observe every layer (Figure 1, Table 1).")
FIGURE("doc_fig1_architecture.png", 15.2, "Layered architecture: LangGraph orchestration over tools and data, with observability across all layers.")
TABLE("Components, technology, responsibility and build status.",
      [["Component", "Technology", "Responsibility", "Owner", "Status"],
       ["Orchestration, HITL, checkpoints", "LangGraph, SqliteSaver", "graph wiring, interrupts, resume", "Srijan", "built"],
       ["Mock portals, identity matching", "FastAPI, SQLite, RapidFuzz", "noisy bank/insurer/registry records; name + DOB + city score", "Chirag", "built (OCR: Review 3)"],
       ["Rule corpus, retrieval, grading", "Markdown, Chroma, nomic-embed-text", "cited claim procedures; retrieve, grade, re-query, abstain", "Manohara", "built"],
       ["Tracing, evaluation, tests", "Langfuse, JSONL/HTML, pytest", "trace every step and LLM call; scorecard vs answer key; 18 tests", "Mohammed", "built (full harness: Review 3/4)"],
       ["LLM", "Llama 3.1 8B via Ollama, temperature 0", "choose next tool; grade borderline rules only", "all", "built, with fixed fallbacks"]],
      [3.5, 3.4, 5.2, 2.1, 2.8])

# ====================================================================== 3
H1("3. Agent graph, state and data flow")
B("A Supervisor validates the input, plans one task per asset type and routes the work.", "Graph: ")
B("Four specialists do the work: Tracer, Rules Expert, Builder, Verifier.", "Agents: ")
B("State is checkpointed in SQLite after every node under thread_id = case_id; a killed process resumes at the exact step.", "Durability: ")
B("Two nodes call interrupt(): identity confirmation (medium match) and final release of the claim pack.", "Human in the loop: ")
FIGURE("doc_fig2_graph.png", 14.8, "The compiled graph, printed from code with --show-graph. Dashed red: Verifier send-back (at most 6 rounds). Blue: human interrupts.")
H2("3.1 Working state (CaseState)")
BL("Inputs and working state", ["case_id, deceased, claimant, scans, plan.",
                               "candidate_assets (record, match score, evidence, identity_confirmed), rejected_candidates.",
                               "applicable_rules (asset → graded rules), abstained."])
BL("Outputs and control", ["claim_packs (status, requirements{doc_code, rule_id, have_it}, missing, notes).",
                          "verifier_feedback, round, llm_calls, human_answers, done.",
                          "Account numbers, PAN and phone are masked before any trace leaves the process."])
H2("3.2 Worked example")
TABLE("Meena's case end to end.",
      [["#", "From → to", "What happens", "Moment"],
       ["1", "Family → Supervisor", "case details; claimant is a legal heir (no nominee); plan: one task each for bank, insurer, shares", ""],
       ["2", "Tracer → bank portal", "LLM picks search_bank; 3 records. 'R. Subramanian' accepted as an initials variant (0.94); two namesakes rejected on date of birth", "1 · name variant"],
       ["3", "Tracer → share registry", "name matches but the address differs (0.65): medium confidence", ""],
       ["4", "Tracer → Family", "'Is this record your relative?' (interrupt, checkpointed); the answer yes is saved to the case file", "3 · ask the family"],
       ["5", "Rules Expert → corpus", "bank query returns BANK-NOM-01 (nominee rule), graded unfit for a legal heir; re-query returns BANK-LH-01", "2 · wrong rule caught"],
       ["6", "Rules Expert", "insurance: no rule fits (the nominee has died) → abstain, 'I don't know'", ""],
       ["7", "Builder → Verifier", "checklist of 5 DOC_* items, each citing its rule", ""],
       ["8", "Verifier → Rules Expert", "V3 fails (name variant, no name-variation proof); BANK-NAME-01 fetched, affidavit added; round 2 passes", "feedback loop"],
       ["9", "Supervisor → Family", "statuses set by fixed code; release approval (interrupt): yes", ""]],
      [0.8, 3.6, 9.6, 3.0], size=8.2)

# ====================================================================== 4
H1("4. Agentic patterns: where, why, and what was rejected")
TABLE("Patterns, placement, rationale and the alternative rejected.",
      [["Pattern", "Where in Waris", "Why chosen", "Alternative rejected"],
       ["Plan-and-execute", "Supervisor plans one task per asset type", "asset types known up front; the plan is auditable", "pure ReAct for everything: unbounded, hard to audit"],
       ["ReAct [3]", "Tracer: LLM picks a portal, observes, picks the next", "the next search depends on what came back", "fixed pipeline: cannot adapt to an empty or failed source"],
       ["Corrective / agentic RAG [4]", "Rules Expert: retrieve → grade → re-query ≤ 2 → abstain", "the most similar rule can be the wrong procedure (nominee vs legal heir)", "plain top-k RAG: the wrong rule passes silently"],
       ["Reflection / critic [5]", "Verifier V1–V5, send back with a reason", "a separate critic catches omissions and can be ablated", "self-check in the Builder: biased, cannot be switched off"],
       ["Supervisor multi-agent", "Supervisor + 4 specialists", "one router holds every limit and safety rule", "peer-to-peer swarm: loops harder to bound"],
       ["Human-in-the-loop", "interrupt() on medium identity match and before release", "a wrong-person match is the worst error", "auto-accept above a threshold: breaks the 0 wrong-person target"],
       ["Durable workflow + memory", "SQLite checkpoint per node; separate case file", "cases run for weeks as documents arrive", "in-memory state: a restart loses the case"]],
      [2.9, 4.5, 4.9, 4.7], size=8.3)

H2("4.1 Fixed code versus LLM")
BL("Fixed code decides", ["Status, citations, identity scores, rule-metadata grading and every limit."])
BL("The LLM only decides", ["Which portal to search next (validated JSON; tool arguments always come from case facts).",
                            "Whether a rule fits, when metadata cannot decide."])
BL("Result", ["Runs are reproducible and testable against an answer key.",
              "If Ollama is slow, wrong or off, a deterministic fallback keeps the run going.",
              "A Meena run uses 3 of 40 LLM calls; with the LLM off the statuses are identical."])

H2("4.2 Agentic RAG and the Verifier")
BL("Retrieval", ["Embeddings come from nomic-embed-text through Ollama (an offline hash vector is the fallback).",
                 "Rules live in a Chroma collection rebuilt at every start.",
                 "Retrieval filters by institution and topic and skips rejected rules."])
BL("Finding", ["With neural embeddings the nominee rule ranks first even for a legal-heir query.",
               "Grading and exclusion, not similarity, produce the correct checklist."])
TABLE("Verifier checks and where a failure is routed.",
      [["Check", "What it verifies", "On failure, send back to"],
       ["V1", "every checklist item has a rule_id", "Builder"],
       ["V2", "that rule exists in the corpus and requires that document", "Builder"],
       ["V3", "a name variant (initials, spelling, order) implies name-variation proof in the checklist", "Rules Expert"],
       ["V4", "a medium-confidence match was confirmed by the family", "identity gate"],
       ["V5", "the pack validates against the ClaimPack schema", "Builder"]],
      [1.8, 11.2, 4.0])

H2("4.3 Limits and identity policy")
TABLE("Hard limits: every loop is bounded.",
      [["Limit", "Value", "When it is hit"],
       ["Verifier rounds per case; same check failing twice", "6; 2", "asset → NEEDS_HUMAN_REVIEW; asset escalated (no ping-pong)"],
       ["RAG re-queries per asset; Tracer steps; LLM calls per case", "2; 8; 40", "abstain (‘I don't know’); stop searching; finalize with fixed fallbacks"],
       ["Tool timeout; retries; invalid LLM JSON", "10 s; 2; 1 retry", "source flagged unavailable, never guessed; then fixed fallback"]],
      [7.2, 2.6, 7.2])
BL("Identity policy", ["Score = 0.5·name + 0.3·DOB + 0.2·city (a missing field counts 0.5).",
                       "A date-of-birth conflict marks a namesake and is rejected outright.",
                       "≥ 0.85 accept; 0.60–0.85 always ask the family; < 0.60 reject.",
                       "Thresholds are tuned on the 40 dev cases only, never on the held-out 20."])

# ====================================================================== 5
H1("5. Data sources and tool plan")
H2("5.1 Mock portals and rule corpus")
BL("Mock portals", ["Three FastAPI portals over SQLite (/bank, /insurer, /registry) return fuzzy, noisy candidates.",
                    "Noise: namesakes (same name, different date of birth), initials, old addresses.",
                    "One record carries injected instruction text to test the prompt-injection guard.",
                    "Portal text is data: only whitelisted fields pass on."])
BL("Rule corpus", ["Six markdown files written from public RBI, IRDAI and IEPF procedure types; each versioned and marked verified: illustrative.",
                   "Front matter: rule_id, institution_type, topic, applies_to (nominee | legal_heir | any), amount_band, requires[DOC_*], version, source_url.",
                   "Twenty fixed DOC_* codes are shared by rules, Builder and answer keys, so checklist precision and recall are computable.",
                   "One situation is deliberately uncovered (insurance claim where the nominee has died) so abstention is testable."])
H2("5.2 Synthetic data pipeline")
BL("Pipeline", ["Generate the hidden true world (person, assets, family).",
                "Write messy portal records from it; write partial family knowledge and scans.",
                "Write the answer key automatically; labels never come from an LLM."])
BL("Scale and status", ["Plan: 60 cases (15 easy, 25 medium, 20 hard), split 40 dev and 20 held-out.",
                        "Every scenario (name variants, namesake, partial info, no assets, several accounts, nominee vs heir, joint account, missing or conflicting documents, missing rule, blurry scans, injection scan) appears at least 3 times.",
                        "Today only the Meena case exists, hand-built to this design; the generator is a Review 3 item."])
H2("5.3 Tool plan")
TABLE("Tools, contracts, callers and failure behaviour.",
      [["Tool", "Input → output", "Called by", "Timeout / failure behaviour", "Status"],
       ["search_bank / insurer / registry", "name, dob?, city? → candidate records", "Tracer", "10 s, retry 2, then flagged unavailable", "built"],
       ["match_name, identity_score", "names / deceased + record → score, variant, band, evidence", "Tracer", "pure functions", "built"],
       ["retrieve_rules, grade_rule", "query, institution, topic, exclude → rule; facts + rule → fits, reason", "Rules Expert", "none left → abstain; metadata first, LLM only if undecidable", "built"],
       ["compute_status", "requirements, flags → READY / MISSING_ITEMS / NEEDS_HUMAN_REVIEW", "Finalize", "pure function", "built"],
       ["ocr_document, draft_letter", "scan → text, fields, confidence; asset, requirements → letter", "Tracer; Builder", "confidence < 0.6 → ask human; template + LLM", "Review 3"]],
      [3.3, 5.4, 2.2, 4.6, 1.5], size=8.2)

# ====================================================================== 6
H1("6. Evaluation and experiment plan")
TABLE("Metrics, definitions and targets. Labels come from the generator, never from an LLM.",
      [["Metric", "Definition", "Target"],
       ["Asset recall", "true assets found / true assets", "high"],
       ["Wrong-person matches", "claimed assets that are namesakes or not true assets", "0 (hard gate)"],
       ["Status accuracy; abstention correctness", "assets with the key's status / assets; NEEDS_HUMAN_REVIEW exactly where the key says", "high"],
       ["Checklist precision / recall / F1", "micro-averaged over DOC_* codes versus the answer key", "high"],
       ["Citation coverage", "requirements with a rule_id that exists in the corpus / all requirements", "100 %"],
       ["Letter quality", "LLM judge with a rubric (correct asset and claimant, documents listed, formal, no invented facts), checked against our own marks on 15 letters, κ ≥ 0.6", "agrees with humans"],
       ["Cost and process", "LLM calls, tool calls, rounds, wall time; re-query rate; share of send-backs that led to a fix; HITL trigger rate and whether warranted", "within caps"]],
      [4.2, 10.2, 2.6])
H2("6.1 Experiments")
B("full Waris beats a one-pass baseline (single retrieval + single LLM call, no grading, re-query, Verifier or HITL) on checklist F1 and abstention correctness.", "H1: ")
B("removing the Verifier lowers recall of the name-variation proof.", "H2: ")
B("removing grading and re-query lowers status accuracy on nominee-vs-heir cases.", "H3: ")
BL("Method", ["3 runs per variant (different seeds); report mean ± spread.",
              "Keep a component only if it adds the agreed gain for its extra calls.",
              "Final numbers come from the 20 held-out cases."])

# ====================================================================== 7
H1("7. Current build status and evidence")
FIGURE("doc_fig3_log.png", 15.0, "Excerpt of a real run (python -m waris.run --case meena) showing identity matching, the injection guard, graded RAG, abstention and the Verifier loop.")
H2("7.1 Evidence")
BL("Scorecard on the Meena case", ["Asset recall 100 %, wrong-person matches 0, status accuracy 100 %.",
                                   "Checklist precision/recall 100 %, citation coverage 100 %, abstention correct.",
                                   "One hand-built case: it shows the harness and system work end to end, not a general result."])
BL("Tests and durability", ["18 automated tests pass.",
                            "A killed process resumes from its checkpoint; a second run reuses the family's earlier answer from the case file."])
BL("Observability", ["Every LLM call is a trace event (model, latency, tokens, JSON answer).",
                     "Traces go to a local HTML file and to Langfuse."])
H2("7.2 Not yet built (Review 3/4) and risks")
BL("Not yet built", ["OCR of scans and claim-letter drafting.",
                     "Seeded 60-case generator and full evaluation harness; LLM-judge validation; A/B and ablation runs.",
                     "Verification of rule details against official sources."])
BL("Risks and mitigations", ["Small local model: the run never depends on it (validated JSON, fixed fallbacks).",
                             "Rule accuracy: labelled illustrative, no legal advice.",
                             "Wrong-person matches: hard gate at 0, ask-on-medium, DOB conflict rejects.",
                             "Faded scans: we generate the scans, so difficulty is controlled."])

H1("References")
for ref in ["[1] Lapaas Voice, “Unclaimed assets cross ₹1.1 lakh crore in FY26”, citing government data to the Lok Sabha.",
            "[2] Moneylife, “Supreme Court seeks response on informing heirs of unclaimed assets”, 6 May 2026.",
            "[3] S. Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models”, ICLR 2023.",
            "[4] S.-Q. Yan et al., “Corrective Retrieval Augmented Generation”, 2024.",
            "[5] N. Shinn et al., “Reflexion: Language Agents with Verbal Reinforcement Learning”, NeurIPS 2023."
            ]:
    P(ref, size=8, after=0)

import os
out = Path(os.environ["WARIS_DOCX_OUT"]) if os.environ.get("WARIS_DOCX_OUT") else HERE / "Waris_Design_Document_Review2.docx"
doc.save(out)
print("saved", out)
