"""Builds docs/Waris_Review2.pptx (13 slides) from the same figures used in the design document.

Run:  python docs/build_pptx.py
Covers exactly what the instructor asked for: architecture diagram (agent/graph, components, data flow),
agentic patterns and why, data sources and tool plan, evaluation plan and metrics, plus a live demo slide.
"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
TEAL, TEAL_L = RGBColor(0x0B, 0x6E, 0x6E), RGBColor(0xDC, 0xEF, 0xEF)
AMBER, AMBER_L = RGBColor(0xE8, 0xA3, 0x3D), RGBColor(0xFB, 0xEF, 0xD9)
INK, GREY, WHITE = RGBColor(0x1F, 0x2D, 0x3D), RGBColor(0x6B, 0x78, 0x85), RGBColor(0xFF, 0xFF, 0xFF)
RED, GREEN, BLUE = RGBColor(0xC0, 0x39, 0x2B), RGBColor(0x2E, 0x8B, 0x57), RGBColor(0x1F, 0x4E, 0x9C)
HEAD, BODY = "Cambria", "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 13


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1.25)
    s.shadow.inherit = False
    return s


def text(slide, x, y, w, h, content, size=16, bold=False, color=INK, font=BODY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.05):
    """content: str or list of str / (str, dict) paragraphs. dict keys: size, bold, color, bullet."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    paras = content if isinstance(content, list) else [content]
    for i, p in enumerate(paras):
        t, o = (p, {}) if isinstance(p, str) else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        if i:
            para.space_before = Pt(o.get("gap", 4))
        r = para.add_run()
        r.text = ("•  " if o.get("bullet") else "") + t
        r.font.size = Pt(o.get("size", size))
        r.font.bold = o.get("bold", bold)
        r.font.color.rgb = o.get("color", color)
        r.font.name = o.get("font", font)
    return tb


def base(title, n, speaker, notes, kicker=None):
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, 13.333, 0.12, TEAL)
    text(s, 0.55, 0.3, 12.2, 0.8, title, size=30, bold=True, color=TEAL, font=HEAD, anchor=MSO_ANCHOR.MIDDLE)
    if kicker:
        text(s, 0.55, 1.05, 12.2, 0.45, kicker, size=15, color=GREY)
    text(s, 0.55, 7.05, 9, 0.3, f"Waris  ·  Review 2: Design & Architecture  ·  presenter: {speaker}", size=10, color=GREY)
    text(s, 12.0, 7.05, 0.8, 0.3, f"{n}/{TOTAL}", size=10, color=GREY, align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = notes
    return s


def picture(slide, path, x, y, w, h):
    im = Image.open(path)
    ar = im.width / im.height
    pw, ph = (w, w / ar) if w / h < ar else (h * ar, h)
    slide.shapes.add_picture(str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


def table(slide, x, y, w, rows, col_w, size=12, row_h=0.42, head_fill=TEAL, first_bold=True):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tb = shp.table
    for j, cw in enumerate(col_w):
        tb.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tb.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            c = tb.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            c.fill.fore_color.rgb = head_fill if i == 0 else (TEAL_L if i % 2 else WHITE)
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = val
            r.font.size = Pt(size)
            r.font.name = BODY
            r.font.bold = i == 0 or (first_bold and j == 0)
            r.font.color.rgb = WHITE if i == 0 else INK
    return tb


def card(slide, x, y, w, h, head, body, fill=TEAL_L, edge=TEAL, size=12.5):
    rect(slide, x, y, w, h, fill, edge, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.04
    text(slide, x + 0.15, y + 0.1, w - 0.3, 0.4, head, size=15, bold=True, color=edge if edge != AMBER else RGBColor(0x9A, 0x62, 0x00), font=HEAD)
    text(slide, x + 0.15, y + 0.55, w - 0.3, h - 0.6, body, size=size)


# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.333, 7.5, TEAL)
rect(s, 0, 5.2, 13.333, 0.08, AMBER)
text(s, 0.8, 1.5, 11.5, 1.2, "Waris", size=72, bold=True, color=WHITE, font=HEAD)
text(s, 0.8, 2.85, 11.5, 0.9, "An Agentic AI System for Unclaimed Inheritance Recovery", size=30, color=WHITE, font=HEAD)
text(s, 0.8, 3.75, 11.5, 0.6, "Review 2: Design & Architecture  ·  with live demo of the working core", size=20, color=AMBER_L)
text(s, 0.8, 5.5, 11.8, 1.4, ["Srijan C Vachadmath (Team Lead)  ·  Chirag T  ·  Manohara Salmani  ·  Mohammed Arshaq",
                              "Agentic AI (26CD7PEAAI)  ·  B.E. CSE (Data Science), Sem VII  ·  BMSCE  ·  Dr. Kalyan Nagaraj"],
     size=16, color=WHITE)
s.notes_slide.notes_text_frame.text = ("SRIJAN. Waris (heir) is a multi-agent system that tells a family, for each asset a deceased relative left, "
                                       "whether the claim is ready to file and exactly what is missing. Today: the design, then a live run of what is built.")

# ---------------------------------------------------------------- 2 problem + decision
s = base("The problem and the one decision", 2, "Srijan",
         "SRIJAN. 30 seconds, recap only. Over 1.1 lakh crore is unclaimed in India; government portals help search, none builds the claim. "
         "Waris supports ONE decision per asset: ready to file, or exactly what is missing. It is advisory: never files, never decides heirship.")
card(s, 0.55, 1.35, 6.0, 2.55, "Meena's family (synthetic)",
     [("Her grandfather Ramaswamy Subramanian died in 2019.", {"bullet": True}),
      ("A fixed deposit, a life policy and 50 shares exist. Nobody knows.", {"bullet": True}),
      ("The bank says 'R. Subramanian'; the death certificate says 'Ramaswamy Subramanian'. One difference can stop a claim.", {"bullet": True})], size=14)
card(s, 6.8, 1.35, 6.0, 2.55, "Why it is open",
     [("₹1.1 lakh crore unclaimed (FY26); banks returned only ₹10,297 cr (Apr 2022 to Nov 2025).", {"bullet": True}),
      ("Supreme Court (May 2026) asked how legal heirs are informed.", {"bullet": True}),
      ("Govt portals SEARCH. None knows each institution's claim rules, fixes mismatches or builds the claim pack.", {"bullet": True})],
     fill=AMBER_L, edge=AMBER, size=14)
rect(s, 0.55, 4.2, 12.25, 1.5, TEAL, None, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.06
text(s, 0.8, 4.3, 11.8, 0.45, "THE DECISION", size=13, bold=True, color=AMBER_L)
text(s, 0.8, 4.7, 11.8, 0.95, "For each asset left behind: is the claim ready to file, and if not, exactly what is missing?",
     size=26, bold=True, color=WHITE, font=HEAD)
table(s, 0.55, 5.95, 12.25, [["Input", "Output per asset", "Final authority"],
                              ["Deceased's details, claimant's relationship and documents", "READY · MISSING_ITEMS · NEEDS_HUMAN_REVIEW, with a cited document checklist",
                               "The family. Waris never moves money, files, or decides heirship"]],
      [3.9, 4.6, 3.75], size=12, row_h=0.45, first_bold=False)

# ---------------------------------------------------------------- 3 architecture
s = base("System architecture", 3, "Srijan",
         "SRIJAN. Four layers. Interface and guardrails on top; a LangGraph orchestration layer with a Supervisor and four specialists; "
         "tools underneath; data at the bottom, including two kinds of memory: checkpoints for resume, a case file that survives new runs. "
         "Langfuse and a local trace watch everything, with personal data masked. The LLM is small and local; it only chooses the next tool and grades borderline rules.",
         kicker="Supervisor + 4 specialists on LangGraph; tools and data underneath; every step traced.")
picture(s, FIG / "fig1_architecture.png", 0.45, 1.5, 12.45, 5.5)

# ---------------------------------------------------------------- 4 graph
s = base("The agent graph (real node names)", 4, "Srijan",
         "SRIJAN. This is the actual compiled graph, not a sketch; we print it from the code with --show-graph. Tracer finds assets, the identity gate pauses for the family on a medium match, "
         "Rules Expert and Builder produce the cited checklist, the Verifier either passes it or sends it back to the agent that can fix it. Round counter capped at six. "
         "Finalize computes status with fixed code; the family approves before anything is released.",
         kicker="Conditional edges, send-back loops, two human interrupts, and a limit guard.")
picture(s, FIG / "fig2_graph.png", 0.45, 1.5, 12.45, 5.5)

# ---------------------------------------------------------------- 5 data flow
s = base("Data flow: Meena's case, step by step", 5, "Srijan",
         "SRIJAN. Follow the numbers. 3: the LLM picks the bank portal. 4: Moment 1, 'R. Subramanian' is accepted as an initials variant, two namesakes are rejected on date of birth. "
         "6: Moment 3, the share record matches the name but not the address, so the run pauses and asks the family. 9 to 10: Moment 2, the nominee rule is graded unfit, the query is refined, the legal-heir rule fits. "
         "13: the Verifier loop: the checklist had no name proof, so it is sent back.",
         kicker="Three moments and the Verifier feedback loop, in the order they happen.")
picture(s, FIG / "fig3_sequence.png", 0.45, 1.45, 12.45, 5.55)

# ---------------------------------------------------------------- 6 patterns
s = base("Agentic patterns: where, why, and what we rejected", 6, "Manohara",
         "MANOHARA. Each pattern has a job and a rejected alternative. The two to stress: corrective RAG, because the most similar rule is often the wrong one, and the separate Verifier, "
         "because a separate critic can be removed for our ablation experiment and a self-check inside the Builder could not.")
table(s, 0.55, 1.3, 12.25, [
    ["Pattern", "Where in Waris", "Why chosen", "Alternative rejected"],
    ["Plan-and-execute", "Supervisor plans one task per asset type", "Asset types are known up front, so the plan is auditable", "Pure ReAct for everything: unbounded, hard to audit"],
    ["ReAct (think, act, observe)", "Tracer picks a portal, reads the result, picks the next", "The next search depends on what came back", "Fixed pipeline: cannot adapt to an empty or failed source"],
    ["Corrective / agentic RAG", "Rules Expert: retrieve, grade, re-query, abstain", "The most similar rule can be the wrong procedure (nominee vs legal heir)", "Plain top-k RAG: the wrong rule passes silently"],
    ["Reflection / critic loop", "Verifier checks V1 to V5, sends work back with a reason", "A separate critic catches omissions and can be ablated", "Self-check inside the Builder: biased, cannot be switched off"],
    ["Supervisor multi-agent", "Supervisor routes to 4 specialists", "One router holds every limit and safety rule", "Peer-to-peer swarm: loops harder to bound"],
    ["Human-in-the-loop", "interrupt() on a medium identity match and before release", "A wrong-person match is the worst possible error", "Auto-accept above a threshold: breaks the 0 wrong-person target"],
    ["Durable workflow + memory", "SQLite checkpoint after every node; separate case file", "Cases run for weeks while documents arrive", "In-memory state: a restart loses the case"],
], [2.35, 3.3, 3.5, 3.1], size=12, row_h=0.66)

# ---------------------------------------------------------------- 7 RAG + identity
s = base("Agentic RAG and the identity policy", 7, "Manohara",
         "MANOHARA. The RAG loop in five steps. Grading is two-stage: a free metadata check first, an LLM only when metadata cannot decide. In our demo the insurance policy shows the abstain path: "
         "the only insurer rule is for nominees, the nominee has died, so there is no trusted rule and Waris says I don't know. The identity policy is why we target zero wrong-person matches: a medium match is never auto-accepted.")
steps = [("1  Query", "built from case facts: institution, claimant type, nominee status"), ("2  Retrieve", "top rule from Chroma, filtered by institution and topic"),
         ("3  Grade", "fit check vs the case: does the rule apply to THIS claimant?"), ("4  Re-query", "unfit: refine query, exclude the rejected rule (max 2)"),
         ("5  Abstain", "nothing fits: \"I don't know\", NEEDS_HUMAN_REVIEW")]
for i, (h, b) in enumerate(steps):
    x = 0.55 + i * 2.48
    rect(s, x, 1.4, 2.3, 1.45, AMBER_L if i == 4 else TEAL_L, AMBER if i == 4 else TEAL, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.06
    text(s, x + 0.1, 1.47, 2.1, 0.4, h, size=15, bold=True, color=TEAL if i != 4 else RGBColor(0x9A, 0x62, 0x00), font=HEAD)
    text(s, x + 0.1, 1.9, 2.1, 0.95, b, size=11.5)
card(s, 0.55, 3.1, 6.0, 3.7, "Seen in the live run", [
    ("bank: BANK-NOM-01 retrieved first (most similar) → UNFIT: rule is for a nominee, claimant is a legal heir → re-query → BANK-LH-01 FITS", {"bullet": True}),
    ("insurance: INS-NOM-01 UNFIT → nothing left → ABSTAIN. The corpus deliberately has no rule for 'nominee also deceased'", {"bullet": True}),
    ("name variant: Verifier asks for name proof → BANK-NAME-01 retrieved and added", {"bullet": True}),
    ("Every checklist item carries a rule_id; the Verifier rejects uncited items", {"bullet": True})], size=14)
card(s, 6.8, 3.1, 6.0, 3.7, "Identity policy (zero wrong-person matches)", [
    ("score = 0.5·name + 0.3·DOB + 0.2·city (missing field = 0.5)", {"bold": True}),
    ("DOB conflict → namesake → rejected outright", {"bullet": True}),
    ("≥ 0.85 strong → accept", {"bullet": True}),
    ("0.60 to 0.85 medium → ALWAYS ask the family (interrupt)", {"bullet": True}),
    ("< 0.60 → reject", {"bullet": True}),
    ("Name variants: exact · initials · spelling · word order (RapidFuzz + hand-written rules)", {"bullet": True}),
    ("Thresholds are tuned on the 40 dev cases only, never the 20 held-out", {"bullet": True})], fill=AMBER_L, edge=AMBER, size=14)

# ---------------------------------------------------------------- 8 fixed vs LLM + limits
s = base("What the LLM decides, what fixed code decides, and the limits", 8, "Srijan",
         "SRIJAN. A deliberate design choice: the local 3B-class model only makes small structured decisions. Status, citations, identity scores and limits are fixed code, so results are reproducible and can be scored against the answer key. "
         "If the LLM is slow, invalid or off, the run falls back to a fixed order and never dies; we proved that today when the first call timed out. Every loop is bounded and hitting a limit sends the asset to a human.")
table(s, 0.55, 1.3, 6.45, [
    ["Decision", "Made by", "Guard"],
    ["Which portal next", "LLM (Llama 3.1 8B, T=0)", "validated JSON; fallback fixed order"],
    ["Identity score and band", "Fixed code", "unit-tested"],
    ["Rule fit (stage 1)", "Fixed code (metadata)", "free, deterministic"],
    ["Rule fit (stage 2)", "LLM, only if undecidable", "never overrides stage 1"],
    ["Citations, checks V1 to V5", "Fixed code", "pydantic schema"],
    ["Status per asset", "Fixed code", "READY / MISSING / REVIEW"],
    ["Letters (Review 3)", "LLM + template", "judge checked vs humans"],
], [2.1, 2.1, 2.25], size=11, row_h=0.5)
table(s, 7.25, 1.3, 5.55, [
    ["Limit", "Value", "When hit"],
    ["Verifier rounds", "6", "asset → NEEDS_HUMAN_REVIEW"],
    ["Same check fails twice", "2", "asset escalated (no ping-pong)"],
    ["RAG re-queries / asset", "2", "abstain: no trusted rule"],
    ["Tracer steps", "8", "stop searching"],
    ["LLM calls / case", "40", "finalize; fixed fallbacks"],
    ["Tool timeout / retries", "10 s / 2", "source flagged unavailable"],
], [2.15, 0.9, 2.5], size=11, row_h=0.5)
card(s, 0.55, 5.45, 12.25, 1.5, "Failure handling and guardrails", [
    ("Portal 5xx or timeout: retry twice, then flag the source, never guess  ·  LLM invalid JSON: one retry, then fixed fallback  ·  OCR confidence below 0.6: ask the human to type the field (Review 3)", {"bullet": True}),
    ("PII (account, PAN, phone) masked in logs and traces  ·  portal text is data: instruction-like text is flagged and dropped  ·  inputs validated (ISO dates, enumerations, known document codes)", {"bullet": True})],
     fill=AMBER_L, edge=AMBER, size=11)

# ---------------------------------------------------------------- 9 data sources
s = base("Data sources: synthetic, with the answers known in advance", 9, "Chirag",
         "CHIRAG. We never use real data. The generator builds the true world first, then writes messy portal records and partial family knowledge from it, and the answer key is generated from the truth, never by an LLM. "
         "Today's slice is Meena's case with three portals, namesakes and one record carrying injected instruction text. The full 60-case set comes in Review 3 to 4, with 20 held out.")
card(s, 0.55, 1.35, 4.0, 3.55, "Mock portals (built)", [
    ("FastAPI + SQLite: /bank, /insurer, /registry", {"bullet": True}),
    ("Fuzzy search returns noisy candidates, like real portals", {"bullet": True}),
    ("Today: 3 bank, 1 insurer, 2 registry records incl. 3 namesakes and one with 'ignore the rules' text", {"bullet": True}),
    ("Planned: injected latency and errors", {"bullet": True})], size=13.5)
card(s, 4.75, 1.35, 4.0, 3.55, "Rule corpus (built)", [
    ("6 markdown rule files, cited, versioned; Chroma index", {"bullet": True}),
    ("Front matter: rule_id, institution, applies_to, topic, requires[DOC_*], version, source_url, verified", {"bullet": True}),
    ("Written from public RBI / IRDAI / IEPF procedure types; marked 'illustrative' until verified", {"bullet": True}),
    ("Deliberate gap: nominee also deceased", {"bullet": True})], size=13.5)
card(s, 8.95, 1.35, 3.85, 3.55, "Document codes", [
    ("20 fixed DOC_* codes shared by rules, Builder and answer keys", {"bullet": True}),
    ("This is what makes checklist precision and recall computable", {"bullet": True}),
    ("Example: DOC_LEGAL_HEIR_CERT, DOC_INDEMNITY_BOND, DOC_NAME_VARIATION_AFFIDAVIT", {"bullet": True})], fill=AMBER_L, edge=AMBER, size=13.5)
text(s, 0.55, 5.05, 12.25, 0.4, "Synthetic data pipeline (planned for the full set; Meena's case is hand-built from the same design)", size=14, bold=True, color=TEAL, font=HEAD)
steps = ["1  Generate the TRUE world (hidden): person, assets, family", "2  Write messy portal records: initials, spellings, old addresses, namesakes",
         "3  Write partial family knowledge: some details, some scans", "4  Auto-write the ANSWER KEY (never an LLM)"]
for i, t in enumerate(steps):
    rect(s, 0.55 + i * 3.1, 5.5, 2.95, 0.85, TEAL_L if i < 3 else AMBER_L, TEAL if i < 3 else AMBER, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.08
    text(s, 0.65 + i * 3.1, 5.55, 2.75, 0.75, t, size=11.5, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.55, 6.45, 12.25, 0.5, "60 cases: 15 easy · 25 medium · 20 hard. Stratified: 40 dev, 20 held-out test. Every scenario (namesake, nominee vs heir, joint account, missing rule, injection scan...) appears at least 3 times.",
     size=12, color=GREY)

# ---------------------------------------------------------------- 10 tool plan
s = base("Tool plan", 10, "Chirag",
         "CHIRAG. Eight tools, each with a clear contract. Six are built and used in today's demo; OCR and letter drafting are planned for Review 3. Every external call has a timeout and a defined failure behaviour, "
         "and the LLM never supplies tool arguments: they come from validated case facts.")
table(s, 0.55, 1.3, 12.25, [
    ["Tool", "Input → output", "Called by", "Timeout / failure behaviour", "Status"],
    ["search_bank / insurer / registry", "name, dob?, city? → candidate records (JSON)", "Tracer", "10 s, retry 2, then 'source unavailable' flagged", "built"],
    ["match_name", "two names → score, variant (exact / initials / order / spelling)", "Tracer", "pure function", "built"],
    ["identity_score", "deceased, record → score, band, evidence", "Tracer", "pure; thresholds tuned on dev set", "built"],
    ["retrieve_rules", "query, institution, topic, exclude → rule chunk", "Rules Expert", "none left → abstain", "built"],
    ["grade_rule", "case facts, rule → fits?, reason, stage", "Rules Expert", "metadata first; LLM only if undecidable", "built"],
    ["compute_status", "requirements, flags → READY / MISSING / REVIEW", "Finalize", "pure function", "built"],
    ["ocr_document", "scan path → text, fields, confidence", "Tracer", "confidence < 0.6 → ask human to type", "Review 3"],
    ["draft_letter", "asset, requirements, claimant → letter text", "Builder", "template + LLM; judged vs humans", "Review 3"],
], [2.55, 3.9, 1.35, 3.55, 0.9], size=11.5, row_h=0.56)
text(s, 0.55, 6.45, 12.25, 0.5, "LLM interface: chat_json() at temperature 0, local Ollama, one retry on invalid JSON, then a deterministic fallback. Arguments to every tool come from validated case facts, never from model text.",
     size=12, color=GREY)

# ---------------------------------------------------------------- 11 evaluation
s = base("Evaluation plan and metrics", 11, "Mohammed",
         "MOHAMMED. Labels come only from the generator. The headline safety metric is wrong-person matches, target zero and a hard gate. Today's scorecard runs on the one case we have, so it shows the harness works; "
         "it is not a result. The experiment is written as hypotheses with a decision rule up front: A/B against a one-pass baseline, then ablations, three repeats, mean and spread, honest reporting of failures.")
table(s, 0.55, 1.3, 7.3, [
    ["Metric", "Definition", "Target"],
    ["Asset recall", "true assets found / true assets", "high"],
    ["Wrong-person matches", "claimed assets that are namesakes", "0 (hard gate)"],
    ["Status accuracy", "assets with the key's status / assets", "high"],
    ["Checklist P / R / F1", "DOC_* codes vs answer key (micro)", "high"],
    ["Abstention correctness", "REVIEW raised exactly where key says", "high"],
    ["Citation coverage", "requirements with a valid rule_id / all", "100%"],
    ["Letter quality", "LLM judge, rubric; checked on 15 human-marked letters (κ ≥ 0.6)", "agrees"],
    ["Cost", "LLM calls, tool calls, rounds, wall time", "within caps"],
], [1.95, 4.2, 1.15], size=11.5, row_h=0.5)
card(s, 8.05, 1.3, 4.75, 3.15, "Experiment (3 repeats, mean ± spread)", [
    ("H1: full Waris beats a one-pass RAG baseline on checklist F1 and abstention", {"bullet": True}),
    ("H2: removing the Verifier lowers recall of the name-proof item", {"bullet": True}),
    ("H3: removing grading and re-query lowers status accuracy on nominee-vs-heir cases", {"bullet": True}),
    ("Decision rule fixed in advance: keep a component if it adds the agreed gain for the extra calls it costs", {"bullet": True})],
     fill=AMBER_L, edge=AMBER, size=12.5)
card(s, 8.05, 4.6, 4.75, 2.25, "Also measured from traces", [
    ("re-query rate · share of send-backs that led to a fix · HITL trigger rate and whether each was warranted", {"bullet": True}),
    ("Data: 60 cases, 40 dev, 20 held-out (final numbers only from held-out)", {"bullet": True})], size=12.5)
rect(s, 0.55, 5.95, 7.3, 0.9, TEAL, None, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.08
text(s, 0.7, 5.98, 7.0, 0.85, ["Harness already runs: scorecard on Meena = recall 100%, 0 wrong-person, status 100%, checklist P/R 100%, citations 100%.",
                               ("One case shows the harness works; it is not a result. Real numbers come from the 60-case run.", {"size": 11, "color": AMBER_L})],
     size=12, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 12 demo
s = base("Live demo: what is built and running now", 12, "All",
         "ALL. Run: python -m waris.run --case meena. Srijan starts it and names the graph. Chirag points at the portal records and the name match (Moment 1). Manohara at the nominee rule being graded unfit and the re-query (Moment 2), "
         "and the insurance abstain. Srijan at the Verifier send-back. The run pauses on the share record (Moment 3): answer y. Mohammed opens the Langfuse trace and the scorecard. "
         "Then show durable resume: run with --exit-at-pause, restart, and it continues from the checkpoint. Backup: this screenshot is a real captured run.",
         kicker="python -m waris.run --case meena   ·   LLM-driven Tracer, real RAG, real Verifier loop, human pause, Langfuse trace")
picture(s, FIG / "fig4_demo_log.png", 0.45, 1.5, 8.55, 5.45)
card(s, 9.2, 1.5, 3.65, 5.35, "What to watch for", [
    ("MOMENT 1  name variant accepted, namesakes rejected on DOB", {"bullet": True, "size": 11.5}),
    ("MOMENT 2  nominee rule UNFIT → re-query → legal-heir rule", {"bullet": True, "size": 11.5}),
    ("MOMENT 3  address differs → run pauses, asks the family", {"bullet": True, "size": 11.5}),
    ("LOOP  Verifier V3 FAIL → rules expert → rebuilt → PASS", {"bullet": True, "size": 11.5}),
    ("ABSTAIN  insurance: no rule → \"I don't know\"", {"bullet": True, "size": 11.5}),
    ("GUARD  injected 'ignore the rules' text dropped", {"bullet": True, "size": 11.5}),
    ("Then: kill at the pause and resume; second run remembers the family's answer; 18 tests pass", {"bullet": True, "size": 11.5, "bold": True})],
     fill=AMBER_L, edge=AMBER, size=11.5)

# ---------------------------------------------------------------- 13 status + next
s = base("Built now vs next, and risks", 13, "Srijan",
         "SRIJAN. Honest status. Everything in the left column ran in the demo. The right column is the plan for Review 3 on the thirty-first and Review 4 on the seventh. Risks: the small local model, OCR on poor scans, and time; "
         "mitigations are that the run never depends on the LLM, scans are generated by us so we control difficulty, and the demo path is already working.")
card(s, 0.55, 1.35, 6.0, 4.35, "Built and demonstrated (Review 2)", [
    ("LangGraph graph: Supervisor + Tracer, Rules Expert, Builder, Verifier", {"bullet": True}),
    ("3 mock portals with namesakes; 6 cited rules in Chroma", {"bullet": True}),
    ("Identity policy; 2-stage rule grading; V1 to V5 Verifier; fixed-code status", {"bullet": True}),
    ("2 human interrupts; SQLite checkpoint resume; case-file memory", {"bullet": True}),
    ("Guardrails: PII masking, injection guard, input validation, limits", {"bullet": True}),
    ("Langfuse + local HTML trace; scorecard vs answer key; 18 tests", {"bullet": True})], size=15.5)
card(s, 6.8, 1.35, 6.0, 4.35, "Next (Review 3 by 31 Oct, Review 4 by 7 Nov)", [
    ("Streamlit screen with approve / reject buttons; OCR on generated scans", {"bullet": True}),
    ("Draft claim letters (template + LLM)", {"bullet": True}),
    ("Seeded generator: 60 cases, answer keys, 20 held out", {"bullet": True}),
    ("Eval harness over all cases; LLM judge validated on 15 letters", {"bullet": True}),
    ("A/B vs one-pass baseline; ablations; 3 repeats; failure analysis", {"bullet": True}),
    ("Verify rule thresholds against official sources", {"bullet": True})], fill=AMBER_L, edge=AMBER, size=15.5)
table(s, 0.55, 5.9, 12.25, [["Risk", "Mitigation"],
                              ["Small local model is unreliable; OCR on faded scans; time before Review 3", "Run never depends on the LLM (fixed fallbacks); we generate the scans so difficulty is controlled; the core path already works end to end"]],
      [4.6, 7.65], size=11.5, row_h=0.45, first_bold=False)

out = HERE / "Waris_Review2.pptx"
prs.save(out)
print("saved", out)
