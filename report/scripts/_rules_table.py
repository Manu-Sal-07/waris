import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = []
for f in sorted((root / "data" / "rules").glob("*.md")):
    t = f.read_text(encoding="utf-8")
    fm = dict(re.findall(r"^(\w+):\s*(.*)$", t.split("---")[1], re.M))
    req = re.findall(r"DOC_[A-Z_]+", fm["requires"])
    short = [r.replace("DOC_", "").replace("_", "\\_") for r in req]
    rid = fm["rule_id"]
    rows.append(f"\\texttt{{{rid}}} & {fm['institution_type']} & {fm['topic'].replace('_', ' ')} & {fm['applies_to'].replace('_', ' ')} & {fm['amount_band']} & \\scriptsize {', '.join(short)} \\\\")
out = "\n".join(rows)
(Path(__file__).parent / "parts" / "rules_rows.tex").write_text(out + "\n", encoding="utf-8")
print(out)
