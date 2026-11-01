"""UI smoke test with Streamlit's AppTest (no browser): the app loads, runs a generated case and shows its parts."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from waris import llm


@pytest.fixture(autouse=True)
def _llm_off():
    yield
    llm.set_enabled(True)


def _app() -> AppTest:
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _start(at: AppTest, case: str) -> AppTest:
    at.sidebar.selectbox[0].set_value(case)
    at.sidebar.checkbox[0].set_value(False)            # LLM off: deterministic and fast
    at.sidebar.button[0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_app_loads_with_four_tabs():
    at = _app()
    assert [t.label for t in at.tabs][:4] == ["Run a case", "Rules & RAG explorer", "Evaluation (60 cases)", "Graph & trace"]
    cases = at.sidebar.selectbox[0].options
    assert len(cases) >= 61 and any(c.startswith("h07") for c in cases)


def test_case_with_scans_conflict_runs_to_the_release_gate_and_finishes():
    at = _start(_app(), "h07")
    assert "Final approval" in " ".join(w.value for w in at.warning)          # waits at the release gate
    next(b for b in at.button if "Approve release" in b.label).click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "disagree" in " ".join(e.value for e in at.error)                  # the document conflict is shown, not hidden
    assert "NEEDS HUMAN REVIEW" in " ".join(m.value for m in at.markdown)


def test_family_question_case_shows_buttons():
    at = _start(_app(), "m15")
    assert "Waris needs the family" in " ".join(w.value for w in at.warning)
    labels = [b.label for b in at.button]
    assert any("Yes, that is him" in l for l in labels) and any("No, different person" in l for l in labels)
