"""Assembles report/Waris_Report.tex from the instructor's template (preamble, title page, certificate kept verbatim)
and the chapter files in report/parts/. Run from anywhere:  python report/build.py [--parts front,ch1,...]"""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent
T = (R.parent / "AAI_AAT_Report" / "Report_Template.tex").read_text(encoding="utf-8").splitlines(keepends=True)
txt = "".join(T)

# ---- preamble up to \begin{document}
pre = txt[: txt.index("\\begin{document}")]
rep = {
    r"\newcommand{\ProjectTitle}{": "{Waris: An Agentic AI System for Unclaimed Inheritance Recovery}",
    r"\newcommand{\HeaderTitle}{": "{Waris: Agentic AI for Unclaimed Inheritance Recovery}",
    r"\newcommand{\TeamNo}{": "{XX}",
}
for key, val in rep.items():
    i = pre.index(key)
    j = pre.index("\n", i)
    pre = pre[:i] + key[:-1] + val + pre[j:]
for a, b in {"a": "Srijan C Vachadmath", "b": "Chirag T", "c": "Manohara Salmani", "d": "Mohammed Arshaq"}.items():
    U = a.upper()
    pre = re.sub(r"\\newcommand\{\\USN%s\}\{[^}]*\}\s+\\newcommand\{\\Name%s\}\{[^}]*\}" % (a, U),
                 lambda m: "\\newcommand{\\USN%s}{1BM23CDXXX}  \\newcommand{\\Name%s}{%s}" % (a, U, b), pre)
pre = pre.replace("\\guidancetrue", "\\guidancefalse", 1)

# ---- title page and certificate (verbatim), from "TITLE PAGE" block up to the Abstract
i = txt.index("%  TITLE PAGE")
i = txt.rfind("%====", 0, i)
j = txt.index("%-------------------- Abstract")
titlepage = txt[i:j]

body_hdr = r"""
%=====================================================================
%  MAIN BODY
%=====================================================================
\clearpage
\ClearShipoutPictureBG
\pagestyle{mainbody}
\fancypagestyle{plain}{\pagestyle{mainbody}}
\pagenumbering{arabic}
"""
parts = ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9", "ch10"]
sel = None
if "--parts" in sys.argv:
    sel = sys.argv[sys.argv.index("--parts") + 1].split(",")
    parts = [p for p in parts if p in sel]


def read(name):
    p = R / "parts" / f"{name}.tex"
    return p.read_text(encoding="utf-8") if p.exists() else ""


out = [pre, "\\begin{document}\n", titlepage, read("front"), body_hdr]
for p in parts:
    out.append(read(p))
    out.append("\n")
out.append(read("back").replace(chr(92)+"input{parts/rules_rows}", read("rules_rows")))
out.append("\n\\end{document}\n")
(R / "Waris_Report.tex").write_text("".join(out), encoding="utf-8")
print("written", R / "Waris_Report.tex", "parts:", parts)
