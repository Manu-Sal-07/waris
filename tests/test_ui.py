"""UI smoke tests with Streamlit's AppTest (no browser): the app loads and the developer path runs a benchmark case.
The document-upload flow itself (file uploader, OCR panel, confirm screen) is exercised in a real browser by
scripts/ui_check.py, because AppTest cannot drive file uploads."""
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


def test_app_loads_with_four_tabs_and_no_case_dropdown_on_the_main_page():
    at = _app()
    assert [t.label for t in at.tabs][:4] == ["File a claim", "Rules & RAG explorer", "Evaluation (60 cases)", "Graph & trace"]
    assert not at.sidebar.selectbox or all("Benchmark case" == s.label for s in at.sidebar.selectbox)   # only inside the developer expander
    assert "Upload the proofs you have" in " ".join(m.value for m in at.markdown)
    assert any("Upload the documents to begin" in i.value for i in at.info)


def test_developer_path_runs_the_classic_case_to_the_family_question():
    at = _app()
    at.sidebar.checkbox[0].set_value(False)                       # LLM off: deterministic and fast
    at.sidebar.selectbox[0].set_value("meena")
    next(b for b in at.sidebar.button if "Run this case" in b.label).click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Waris needs the family" in " ".join(w.value for w in at.warning)
    labels = [b.label for b in at.button]
    assert any("Yes, that is him" in l for l in labels) and any("No, different person" in l for l in labels)
    next(b for b in at.button if "Yes, that is him" in b.label).click()
    at.run()
    next(b for b in at.button if "Approve release" in b.label).click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "NEEDS HUMAN REVIEW" in " ".join(m.value for m in at.markdown)               # the insurance policy: "I don't know"
