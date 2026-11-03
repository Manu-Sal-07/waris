"""Langfuse screenshots for the report: the trace tree of the classic family and the detail of one LLM event."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path(__file__).resolve().parent / "figures"
out.mkdir(exist_ok=True)
trace_id = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1050, "height": 2750})
    pg.goto("http://localhost:3001/auth/sign-in")
    pg.wait_for_selector('input[type="email"], input[name="email"]', timeout=60000)
    pg.fill('input[type="email"], input[name="email"]', "waris@example.com")
    pg.fill('input[type="password"]', "waris-demo-pass")
    pg.get_by_role("button", name="Sign in").click()
    pg.wait_for_timeout(4000)
    pg.goto(f"http://localhost:3001/project/waris/traces/{trace_id}")
    pg.wait_for_timeout(7000)
    pg.screenshot(path=str(out / "langfuse_tree_s.png"))
    pg.get_by_text("llm.LLM").first.click()
    pg.wait_for_timeout(3000)
    pg.screenshot(path=str(out / "langfuse_llm_s.png"))
    pg.get_by_text("rules_expert.GRADE").first.click()
    pg.wait_for_timeout(2500)
    pg.screenshot(path=str(out / "langfuse_grade_s.png"))
    b.close()
print("done")
