"""Second UI shoot: the finished claim packs and a drafted letter (scrolls the Streamlit main pane to them)."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
out = Path(__file__).resolve().parent / "figures"
files = [str(p) for p in sorted((ROOT / "demo_proofs" / "ramaswamy_subramanian_demo").glob("*.png"))]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1700, "height": 1350}, device_scale_factor=1.6)
    pg.goto("http://localhost:8501")
    pg.wait_for_selector("text=Upload the proofs you have", timeout=300000)
    pg.locator('input[type="file"]').first.set_input_files(files)
    pg.wait_for_selector("text=What Waris read", timeout=300000)
    pg.wait_for_timeout(2500)
    pg.get_by_role("button", name="Start", exact=False).first.click()
    pg.wait_for_selector("text=Waris needs the family", timeout=600000)
    pg.get_by_role("button", name="Yes, that is him").click()
    pg.wait_for_selector("text=Final approval", timeout=600000)
    pg.get_by_role("button", name="Approve release").click()
    pg.wait_for_selector("text=Claim packs", timeout=120000)
    pg.wait_for_timeout(2500)
    pg.get_by_text("Claim packs", exact=True).first.scroll_into_view_if_needed()
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(out / "ui_packs_raw.png"))
    pg.get_by_text("Claim letters (drafts for the family to review)").first.scroll_into_view_if_needed()
    pg.get_by_text("Letter for bank_deposit", exact=False).first.click()
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / "ui_letter_raw.png"))
    b.close()
print("ui2 done")
