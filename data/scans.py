"""Draws synthetic scanned documents with Pillow and degrades them (rotate / blur / fade).

Used only by the data generator. The generator then reads every scan back with the real OCR tool and checks that
each scan is readable or unreadable exactly as designed, so the answer key never depends on luck.
"""
import random
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

_FONT = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
PAPER = "#F7F3E8"
W, H = 1000, 620

TITLES = {"DOC_DEATH_CERT": "DEATH CERTIFICATE", "DOC_LEGAL_HEIR_CERT": "LEGAL HEIR CERTIFICATE",
          "DOC_CLAIMANT_KYC": "IDENTITY PROOF", "DOC_FD_RECEIPT": "FIXED DEPOSIT RECEIPT"}


def _lines(doc_code: str, f: dict) -> list[str]:
    if doc_code == "DOC_DEATH_CERT":
        return [f"Name: {f['name']}", f"Date of Birth: {f['dob']}", f"Date of Death: {f['dod']}", f"Place: {f['city']}"]
    if doc_code == "DOC_LEGAL_HEIR_CERT":
        return [f"Name of deceased: {f['name']}", f"Heir: {f['heir']}", f"Relationship: {f['relationship']}",
                "Issued by: Tahsildar"]
    if doc_code == "DOC_CLAIMANT_KYC":
        return [f"Name: {f['name']}", f"ID: {f['id']}", f"City: {f['city']}"]
    return [f"Account holder: {f['name']}", f"Account: {f['acct']}", f"Amount: Rs {f['amount']}"]


def render(doc_code: str, fields: dict, degrade: str = "clean", seed: int = 0, extra_line: str = "") -> Image.Image:
    """degrade: clean | rotated | blurry | faded. `extra_line` is printed at the bottom (used for the injection test)."""
    rng = random.Random(seed)
    big, mid, small = (ImageFont.truetype(str(_FONT), s) for s in (46, 34, 26))
    ink = "#1b1b1b"
    if degrade == "faded":
        ink = "#CFC8B5"                       # washed-out ink on old paper
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([14, 14, W - 14, H - 14], outline="#8A8470", width=4)
    d.text((50, 40), TITLES[doc_code], fill=ink, font=big)
    y = 150
    for line in _lines(doc_code, fields):
        d.text((50, y), line, fill=ink, font=mid)
        y += 66
    if extra_line:
        d.text((50, H - 90), extra_line, fill=ink, font=small)
    if degrade == "blurry":
        img = img.filter(ImageFilter.GaussianBlur(6.5))
    elif degrade == "faded":
        img = ImageEnhance.Contrast(img).enhance(0.5).filter(ImageFilter.GaussianBlur(2.0))
    elif degrade == "rotated":
        img = img.rotate(rng.choice([-1, 1]) * rng.uniform(5, 11), expand=True, fillcolor=PAPER, resample=Image.BICUBIC)
    return img
