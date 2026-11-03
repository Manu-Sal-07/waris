"""One-off: add short captions (for the lists of figures and tables), fix two layout details. Run once."""
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "parts"
M = {
    "Architecture of Waris. Blue boxes": "Architecture of Waris",
    "Control flow of the LangGraph": "Control flow of the LangGraph state graph",
    "Sequence of messages": "Message sequence of the worked example",
    "Langfuse trace of the worked example, first half.": "Langfuse trace of the worked example (first half)",
    "Langfuse trace of the worked example, second half.": "Langfuse trace of the worked example (second half)",
    "Interface after the worked example": "Interface after the worked example: claim packs",
    "Document degradations": "Document degradations in the benchmark",
    "``What Waris read''": "``What Waris read'' panel",
    "Live timeline": "Live timeline and identity question",
    "Share of fully correct runs": "Fully correct runs by difficulty",
    "Held-out test families: status accuracy": "Status accuracy, F1 and fully correct cases (test families)",
    "The three proof documents": "Proof documents of the worked example",
    "Comparison of related approaches": "Comparison of related approaches with Waris",
    "Non-functional requirements,": "Non-functional requirements",
    "Data sources. All data": "Data sources",
    "Components, their inputs": "Components and failure behaviour",
    "Design patterns, where": "Design patterns",
    "Worked example: the data": "Worked example: data at each step",
    "Coverage of the ten": "Coverage of the ten agentic concepts",
    "Tools. All portals": "Tools",
    "Technology stack with": "Technology stack",
    "Results on the 20 held-out": "Results on the held-out test families",
    "Key results on the larger": "Key results on the larger sets",
    "Failure modes of the variants": "Failure modes of the variants",
    "Controlled comparisons": "Controlled comparisons on the held-out families",
    "Failure modes, their effects": "Failure modes and mitigations",
}
for p in D.glob("*.tex"):
    s = p.read_text(encoding="utf-8")
    t = s
    for k, v in M.items():
        t = t.replace("\\caption{" + k, "\\caption[" + v + "]{" + k)
    if p.name == "back.tex":
        t = t.replace("\\section{Input Documents of the Worked Example}\n\\begin{figure}[t]", "\\section{Input Documents of the Worked Example}\n\\begin{figure}[H]")
        t = t.replace("\\includegraphics[width=\\linewidth]{figures/fig_langfuse_b.png}", "\\includegraphics[height=0.62\\textheight,keepaspectratio]{figures/fig_langfuse_b.png}")
        for tag in ("\\tiny",):
            pass
        i = t.index("\\chapter{Prompts}")
        j = t.index("\\chapter{Rule Corpus}")
        t = t[:i] + t[i:j].replace("\\ttfamily\\tiny", "\\ttfamily\\scriptsize") + t[j:]
    if t != s:
        p.write_text(t, encoding="utf-8")
        print("updated", p.name)
f = D / "front.tex"
s = f.read_text(encoding="utf-8")
s = s.replace("\\listoffigures\n\\addcontentsline{toc}{chapter}{List of Figures}\n\\listoftables\n\\addcontentsline{toc}{chapter}{List of Tables}",
              "\\clearpage\\phantomsection\\addcontentsline{toc}{chapter}{List of Figures}\n\\listoffigures\n\\clearpage\\phantomsection\\addcontentsline{toc}{chapter}{List of Tables}\n\\listoftables")
f.write_text(s, encoding="utf-8")
print("front ok", "phantomsection" in s)
