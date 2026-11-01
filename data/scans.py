"""Draws synthetic proof documents with Pillow and degrades them (rotate / blur / fade).

Used only by the data generator. The generator then reads every document back with the real OCR tool and checks that
each one is recognised and readable or unreadable exactly as designed, so the answer key never depends on luck.
"""
import random
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from waris.tools.ocr import TITLES

_TTF = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_TRIES = [("DejaVuSans.ttf", 34), ("DejaVuSerif.ttf", 34), ("DejaVuSans.ttf", 36), ("DejaVuSerif.ttf", 32), ("DejaVuSans.ttf", 32)]
PAPER = "#F7F3E8"
W = 1000


def lines_for(doc_code: str, f: dict) -> list[str]:
    if doc_code == "DOC_DEATH_CERT":
        out = [f"Name: {f['name']}", f"Date of Birth: {f.get('dob') or 'not recorded'}", f"Date of Death: {f['dod']}",
               f"Place: {f['city']}"]
        if f.get("aka"):
            out.append(f"Also known as: {f['aka']}")
        return out
    if doc_code == "DOC_CLAIMANT_KYC":
        return [f"Name: {f['name']}", f"ID: {f['id']}", f"City: {f['city']}"]
    if doc_code == "DOC_RELATIONSHIP_PROOF":
        out = [f"Name of deceased: {f['deceased']}"]
        if f.get("dob"):
            out.append(f"Deceased born: {f['dob']}")
        return out + [f"Claimant: {f['claimant']}", f"Relationship: {f['relationship']}"]
    if doc_code == "DOC_LEGAL_HEIR_CERT":
        return [f"Name of deceased: {f['deceased']}", f"Heir: {f['claimant']}", f"Relationship: {f['relationship']}",
                "Issued by: Tahsildar"]
    return [f"Deceased: {f['deceased']}", f"Claimant: {f['claimant']}"]            # every other form


def render(doc_code: str, fields: dict, degrade: str = "clean", seed: int = 0, extra_line: str = "", font: tuple = FONT_TRIES[0]) -> Image.Image:
    """degrade: clean | rotated | blurry | faded. `extra_line` is printed at the bottom (used for the injection test)."""
    rng = random.Random(seed)
    lines = lines_for(doc_code, fields)
    h = max(620, 150 + 66 * len(lines) + 150)
    big, mid, small = (ImageFont.truetype(str(_TTF / font[0]), s) for s in (44, font[1], 26))
    ink = "#CFC8B5" if degrade == "faded" else "#1b1b1b"                # washed-out ink on old paper
    img = Image.new("RGB", (W, h), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([14, 14, W - 14, h - 14], outline="#8A8470", width=4)
    d.text((50, 40), TITLES[doc_code], fill=ink, font=big)
    y = 150
    for line in lines:
        d.text((50, y), line, fill=ink, font=mid)
        y += 66
    if extra_line:
        d.text((50, h - 90), extra_line, fill=ink, font=small)
    if degrade == "blurry":
        img = img.filter(ImageFilter.GaussianBlur(6.5))
    elif degrade == "faded":
        img = ImageEnhance.Contrast(img).enhance(0.5).filter(ImageFilter.GaussianBlur(2.0))
    elif degrade == "rotated":
        img = img.rotate(rng.choice([-1, 1]) * rng.uniform(5, 11), expand=True, fillcolor=PAPER, resample=Image.BICUBIC)
    return img
