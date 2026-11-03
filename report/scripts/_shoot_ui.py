"""Takes the UI screenshots used in the report (run once; Streamlit on :8501, Ollama running). LLM stays ON so the timeline shows real LLM events."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
out = Path(__file__).resolve().parent / "figures"
out.mkdir(exist_ok=True)
files = [str(p) for p in sorted((ROOT / "demo_proofs" / "ramaswamy_subramanian_demo").glob("*.png"))]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1200}, device_scale_factor=1.6)
    pg.goto("http://localhost:8501")
    pg.wait_for_selector("text=Upload the proofs you have", timeout=300000)
    pg.locator('input[type="file"]').first.set_input_files(files)
    pg.wait_for_selector("text=What Waris read", timeout=300000)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=str(out / "ui_upload_raw.png"), full_page=True)
    pg.get_by_role("button", name="Start", exact=False).first.click()
    pg.wait_for_selector("text=Waris needs the family", timeout=600000)
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(out / "ui_question_raw.png"), full_page=True)
    pg.get_by_role("button", name="Yes, that is him").click()
    pg.wait_for_selector("text=Final approval", timeout=600000)
    pg.get_by_role("button", name="Approve release").click()
    pg.wait_for_selector("text=Claim packs", timeout=120000)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=str(out / "ui_result_raw.png"), full_page=True)
    b.close()
print("ui shots done")
