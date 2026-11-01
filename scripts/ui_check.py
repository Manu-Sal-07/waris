"""Real-browser walkthrough of the documents-first UI (needs `streamlit run app/streamlit_app.py` on port 8501 and Chrome).

    .venv\\Scripts\\python scripts\\ui_check.py [outdir]

For four families it does what an evaluator does: select ALL images of a proof folder, read what Waris read, press Start, answer
the family question if one appears, approve the release, and take a screenshot. Checks that nothing raised a Streamlit exception.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "ui_check"
OUT.mkdir(parents=True, exist_ok=True)
INDEX = {c["case_id"]: c["folder"] for c in json.loads((ROOT / "data" / "cases" / "index.json").read_text(encoding="utf-8"))}
FAMILIES = [("classic demo", "ramaswamy_subramanian_demo", "meena"), ("document conflict", INDEX["h07"], "h07"),
            ("later documents", INDEX["m15"], "m15"), ("injection + blurry certificate", INDEX["h13"], "h13")]


def files_of(folder: str, sub: str = "") -> list[str]:
    return [str(p) for p in sorted((ROOT / "demo_proofs" / folder / sub).glob("*.png"))]


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://localhost:8501")
    page.wait_for_selector("text=Upload the proofs you have", timeout=300000)
    page.locator('[data-testid="stSidebar"] label:has-text("Use local LLM")').click()          # LLM off: fast and deterministic
    for label, folder, tag in FAMILIES:
        page.on("dialog", lambda d: d.dismiss())
        page.reload()
        page.wait_for_selector("text=Upload the proofs you have", timeout=300000)
        page.locator('[data-testid="stSidebar"] label:has-text("Use local LLM")').click()
        page.locator('input[type="file"]').first.set_input_files(files_of(folder))
        page.wait_for_selector("text=What Waris read", timeout=300000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / f"{tag}_1_read.png"), full_page=True)
        page.get_by_role("button", name="Start", exact=False).first.click()
        page.wait_for_selector("text=Final approval", timeout=300000) if tag in ("h07", "h13") else page.wait_for_selector(
            "text=Waris needs the family", timeout=300000)
        if page.locator("text=Waris needs the family").count():
            page.get_by_role("button", name="Yes, that is him").click()
            page.wait_for_selector("text=Final approval", timeout=300000)
        page.get_by_role("button", name="Approve release").click()
        page.wait_for_selector("text=Claim packs", timeout=60000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / f"{tag}_2_result.png"), full_page=True)
        if tag == "m15":                                  # a second session: the missing documents arrive
            page.locator('input[type="file"]').nth(1).set_input_files(files_of(folder, "later"))
            page.get_by_role("button", name="Re-check with these documents").click()
            page.wait_for_selector("text=Final approval", timeout=300000)
            page.get_by_role("button", name="Approve release").click()
            page.wait_for_selector("text=Claim packs", timeout=60000)
            page.wait_for_timeout(2000)
            page.screenshot(path=str(OUT / f"{tag}_3_after_later_documents.png"), full_page=True)
        print(f"{label:<34} ok   exceptions on page: {page.locator('[data-testid=\"stException\"]').count()}")
    print("page errors:", errors)
    browser.close()
