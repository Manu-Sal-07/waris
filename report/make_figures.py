"""Builds the raster figures of the report (document montages, annotated Langfuse and UI crops). Run from the repo root."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parent
F = R / "figures"
P = R.parent / "demo_proofs"
FONT = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)


def badge(img, xy, n, r=22):
    d = ImageDraw.Draw(img)
    x, y = xy
    d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 30, 30), outline="white", width=3)
    w = d.textlength(str(n), font=FONT)
    d.text((x - w / 2, y - 18), str(n), fill="white", font=FONT)


def frame(img, w=3):
    out = Image.new("RGB", (img.width + 2 * w, img.height + 2 * w), (110, 110, 110))
    out.paste(img.convert("RGB"), (w, w))
    return out


def hstack(imgs, gap=24, bg="white"):
    h = max(i.height for i in imgs)
    out = Image.new("RGB", (sum(i.width for i in imgs) + gap * (len(imgs) - 1), h), bg)
    x = 0
    for i in imgs:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def captioned(img, text, size=46):
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
    out = Image.new("RGB", (img.width, img.height + size + 14), "white")
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    w = d.textlength(text, font=f)
    d.text(((img.width - w) / 2, img.height + 4), text, fill=(40, 40, 40), font=f)
    return out


# ---- 1. the three proof documents of the classic family
docs = [frame(Image.open(P / "ramaswamy_subramanian_demo" / n)) for n in
        ("01_death_certificate.png", "02_claimant_id.png", "03_relationship_proof.png")]
docs = [captioned(d, t) for d, t in zip(docs, ("(a) death certificate", "(b) claimant's ID", "(c) proof of relationship"))]
hstack(docs).save(F / "fig_docs_classic.png")

# ---- 2. degradations: clean / rotated / blurry / faded (death certificate or ID)
cases = [("sundaram_iyer_easy", "01_death_certificate.png", "(a) clean"),
         ("thyagarajan_subramanian_easy", None, "(b) rotated"),
         ("narasimhan_rao_hard", "01_death_certificate.png", "(c) blurry"),
         ("sundaram_pillai_hard", "02_claimant_id.png", "(d) faded")]
tiles = []
for folder, name, cap in cases:
    d = P / folder
    if name is None:
        name = sorted(p.name for p in d.glob("*.png"))[0]
    im = Image.open(d / name).convert("RGB")
    im.thumbnail((620, 400))
    tiles.append(captioned(frame(im), cap))
top = hstack(tiles[:2])
bot = hstack(tiles[2:])
W = max(top.width, bot.width)
out = Image.new("RGB", (W, top.height + bot.height + 20), "white")
out.paste(top, (0, 0))
out.paste(bot, (0, top.height + 20))
out.save(F / "fig_degradations.png")

# ---- 3. Langfuse: LLM event + tree (tracer part)
llm = Image.open(F / "langfuse_llm_s.png").convert("RGB")
panel = llm.crop((215, 270, 765, 880))
tree = llm.crop((775, 255, 1050, 1370))
fig = Image.new("RGB", (panel.width + tree.width + 30, max(panel.height, tree.height)), "white")
fig.paste(frame(panel), (0, 0))
fig.paste(frame(tree), (panel.width + 30, 0))
badge(fig, (535, 110), 1)
badge(fig, (535, 330), 2)
badge(fig, (535, 530), 3)
ox = panel.width + 30
badge(fig, (ox + 245, 70), 4)                              # trace root
badge(fig, (ox + 245, 305), 5)                             # OCR events
badge(fig, (ox + 245, 420), 6)                             # llm.LLM
badge(fig, (ox + 245, 590), 7)                             # MATCH
fig.save(F / "fig_langfuse_a.png")

# ---- 4. Langfuse: GRADE detail + rules_expert part of the tree
gr = Image.open(F / "langfuse_grade_s.png").convert("RGB")
panel = gr.crop((215, 270, 765, 780))
tree = gr.crop((775, 1500, 1050, 2750))
fig = Image.new("RGB", (panel.width + tree.width + 30, max(panel.height, tree.height)), "white")
fig.paste(frame(panel), (0, 0))
fig.paste(frame(tree), (panel.width + 30, 0))
ox = panel.width + 30
badge(fig, (535, 110), 1)
badge(fig, (535, 300), 2)
badge(fig, (ox + 245, 52), 3)
badge(fig, (ox + 245, 205), 4)
badge(fig, (ox + 245, 520), 5)
badge(fig, (ox + 245, 810), 6)
fig.save(F / "fig_langfuse_b.png")

# ---- 5. UI crops
q = Image.open(F / "ui_question_raw.png").convert("RGB")
read = q.crop((600, 480, 1400, 1680))
read.save(F / "fig_ui_read.png")
tl = q.crop((1480, 90, 2280, 1260))
tl.save(F / "fig_ui_question.png")
print("figures built")
Image.open(F / "ui_packs_raw.png").convert("RGB").crop((598, 650, 1557, 1904)).save(F / "fig_ui_packs.png")
