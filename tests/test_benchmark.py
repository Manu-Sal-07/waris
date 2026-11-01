"""Benchmark tests: the 60-case generator, the OCR/intake path, letters, baseline, ablations, judge and metrics.

Scenario tests run the real graph on generated cases with the LLM switched off (fixed fallbacks), so they are fast and
deterministic; set WARIS_TEST_ALL=1 to run every one of the 60 cases.
"""
import json
import os
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from data import generate_cases as gen
from eval import judge, run_eval
from eval.metrics import score_case
from waris import baseline, config, llm
from waris.agents import letters
from waris.guardrails import validate_case_input
from waris.tools import ocr, portals, retrieval

IDX = json.loads((config.CASES_DIR / "index.json").read_text(encoding="utf-8"))
SPLIT = json.loads((config.CASES_DIR / "split.json").read_text(encoding="utf-8"))
CATALOGUE = ["clean", "name_initials", "name_spelling", "name_translit", "name_order", "name_maiden", "namesake",
             "namesake_ambiguous", "partial_info", "no_assets", "multi_account", "claimant_nominee", "claimant_legal_heir",
             "amount_small", "amount_large", "joint_account", "docs_missing", "doc_conflict", "no_rule", "later_session",
             "scan_clean", "scan_rotated", "scan_blurry", "scan_faded", "scan_inject", "tool_fault"]


@pytest.fixture(scope="module", autouse=True)
def _env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("bench")
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "CASE_FILE_DB", tmp / "case_files.db")
    mp.setattr(config, "CHROMA_DIR", tmp / "chroma")
    from portals.app import app
    portals.set_client(TestClient(app, base_url="http://waris-portals"))
    retrieval.index_rules()
    yield tmp
    portals.set_client(None)
    portals.set_case(None)
    llm.set_enabled(True)
    config.ABLATE.clear()
    mp.undo()


# ---------------------------------------------------------------- data generator
def test_generator_is_deterministic():
    a, b = gen.build_case(next(r for r in gen.recipes() if r.id == "h01")), gen.build_case(next(r for r in gen.recipes() if r.id == "h01"))
    assert a["input"] == b["input"] and a["key"] == b["key"]
    assert [x["holder_name"] for x in a["rows"]["bank"]] == [x["holder_name"] for x in b["rows"]["bank"]]


def test_sixty_cases_with_the_specified_mix_and_split():
    assert len(IDX) == 60
    assert Counter(c["difficulty"] for c in IDX) == {"easy": 15, "medium": 25, "hard": 20}
    assert len(SPLIT["dev"]) == 40 and len(SPLIT["test"]) == 20 and not set(SPLIT["dev"]) & set(SPLIT["test"])
    assert Counter(next(c["difficulty"] for c in IDX if c["case_id"] == i) for i in SPLIT["test"]) == {"easy": 5, "medium": 8, "hard": 7}


def test_every_catalogue_scenario_appears_at_least_three_times():
    counts = Counter(t for c in IDX for t in c["tags"])
    assert [t for t in CATALOGUE if counts[t] < 3] == []


def test_inputs_validate_and_keys_are_consistent():
    for c in IDX:
        d = config.CASES_DIR / c["case_id"]
        case = json.loads((d / "input.json").read_text(encoding="utf-8"))
        key = json.loads((d / "answer_key.json").read_text(encoding="utf-8"))
        validate_case_input({k: case[k] for k in ("case_id", "deceased", "claimant", "scans")})
        for a in key["assets"]:
            assert set(a["missing"]) <= set(a["required_docs"])
            if a["status"] == "READY":
                assert not a["missing"]
            if a["status"] == "MISSING_ITEMS":
                assert a["missing"]
        for s in case["scans"]:
            assert (d / s).exists()


def test_generator_self_check_agrees_with_the_identity_policy_and_ocr():
    r = next(r for r in gen.recipes() if r.id == "h05")
    assert gen.validate(gen.build_case(r), ocr=False) == []


# ---------------------------------------------------------------- OCR and intake
def test_ocr_reads_clean_and_rotated_scans_and_refuses_blurry_ones():
    ok = ocr.read_scan(config.CASES_DIR / "e11" / "scans" / "death_certificate.png")
    assert ok["readable"] and ok["doc_code"] == "DOC_DEATH_CERT" and ok["fields"]["dob"]
    assert ocr.read_scan(config.CASES_DIR / "e14" / "scans" / "death_certificate.png")["readable"]       # rotated
    bad = ocr.read_scan(config.CASES_DIR / "h13" / "scans" / "death_certificate.png")                    # blurry
    assert not bad["readable"]


# ---------------------------------------------------------------- scenarios, end to end
REPRESENTATIVE = ["e01", "e04", "e11", "m01", "m03", "m07", "m10", "m12", "m15", "m18", "m22", "m23", "m25", "h01", "h04", "h05",
                  "h07", "h10", "h12", "h13", "h14", "h16", "h18", "h19", "h20"]
CASES = [c["case_id"] for c in IDX] if os.getenv("WARIS_TEST_ALL") else REPRESENTATIVE


@pytest.mark.parametrize("cid", CASES)
def test_scenario_matches_answer_key(cid, tmp_path):
    row = run_eval.run_one(cid, "full_nollm", 0, tmp_path, save_letters=False)
    assert row["status_accuracy"] == 1.0, row["detail"]
    assert row["wrong_person_matches"] == 0
    assert row["abstention_correct"] and row["conflict_ok"] and row["tool_error_ok"]
    assert row["checklist_precision"] == 1.0 and row["checklist_recall"] == 1.0
    assert row["citation_coverage"] == 1.0
    assert row["question_precision"] == 1.0 and row["question_recall"] == 1.0
    assert row["reasked_in_session2"] == 0


def test_injection_in_a_scan_is_flagged_and_does_not_change_the_result(tmp_path):
    row = run_eval.run_one("h13", "full_nollm", 0, tmp_path, save_letters=False)
    assert row["injection_flagged"] and row["status_accuracy"] == 1.0


def test_namesake_and_ambiguous_record_are_never_claimed(tmp_path):
    for cid in ("h01", "h04", "h12"):
        assert run_eval.run_one(cid, "full_nollm", 0, tmp_path, save_letters=False)["wrong_person_matches"] == 0


def test_no_assets_case_claims_nothing(tmp_path):
    row = run_eval.run_one("m18", "full_nollm", 0, tmp_path, save_letters=False)
    assert row["statuses"] == {} and row["n_truth"] == 0 and row["wrong_person_matches"] == 0


# ---------------------------------------------------------------- letters
FACTS = {"deceased": "Ramaswamy Subramanian", "dod": "2019-06-21", "claimant": "Meena Krishnan", "relationship": "granddaughter",
         "claimant_type": "legal_heir", "product": "fixed deposit", "holder": "R. Subramanian", "ref": "*******4471", "inst": "bank",
         "enclosed": ["DOC_DEATH_CERT"], "to_follow": ["DOC_LEGAL_HEIR_CERT", "DOC_NAME_VARIATION_AFFIDAVIT"]}


def test_letter_lists_enclosed_and_pending_documents_and_the_name_difference():
    text = letters.render(FACTS, letters.template_paragraph(FACTS))
    assert "Documents enclosed with this letter:" in text and "Death certificate" in text
    assert "Documents I will submit shortly:" in text and "Legal heir certificate" in text
    assert "R. Subramanian" in text and "will follow" in text and "files nothing" in text


def test_llm_paragraph_is_validated():
    good = ("I am Meena Krishnan, the granddaughter of the late Ramaswamy Subramanian, who passed away on 2019-06-21. "
            "I am writing to start the claim for the fixed deposit held in his name and kindly request your guidance on the "
            "documents still required from me.")
    assert letters.paragraph_ok(good, FACTS)
    assert not letters.paragraph_ok(good + " The bank guarantees payment within 7 days.", FACTS)       # promise
    assert not letters.paragraph_ok(good.replace("Meena Krishnan", "Someone Else"), FACTS)               # wrong name
    assert not letters.paragraph_ok(good.replace("who passed away on 2019-06-21", "which matured on 2019-06-21"), FACTS)   # invented fact
    assert not letters.paragraph_ok(good + " I am entitled to the proceeds.", FACTS)
    assert not letters.paragraph_ok(good + " Amount 500000 will be paid " * 3, FACTS)                    # invented number
    assert not letters.paragraph_ok("Too short.", FACTS)


def test_letters_are_written_for_claimable_assets_only(tmp_path):
    for cid, n in (("e04", 1), ("h10", 1)):                       # h10: one asset abstained -> no letter for it
        config.LETTER_LLM = False
        row = run_eval.run_one(cid, "full_nollm", 0, tmp_path, save_letters=False)
        assert row["letters"] == n


# ---------------------------------------------------------------- baseline, ablations, judge, metrics
def test_baseline_trusts_the_top_rule_without_grading():
    llm.disable()
    portals.set_case("e04")
    case = json.loads((config.CASES_DIR / "e04" / "input.json").read_text(encoding="utf-8"))
    state = baseline.run_baseline(case)
    pack = next(iter(state["claim_packs"].values()))
    assert pack["notes"][0].startswith("baseline") and state["verifier_feedback"] == [] and state["human_answers"] == []


def test_without_the_verifier_the_name_affidavit_is_missed(tmp_path, monkeypatch):
    monkeypatch.setitem(run_eval.VARIANTS["no_verifier"], "llm", False)
    full = run_eval.run_one("m01", "full_nollm", 0, tmp_path, save_letters=False)
    ablated = run_eval.run_one("m01", "no_verifier", 0, tmp_path, save_letters=False)
    assert full["checklist_recall"] == 1.0 and ablated["checklist_recall"] < 1.0 and ablated["rounds"] == 1


def test_without_grading_the_wrong_rule_is_trusted(tmp_path, monkeypatch):
    monkeypatch.setitem(run_eval.VARIANTS["no_grading"], "llm", False)
    row = run_eval.run_one("m01", "no_grading", 0, tmp_path, save_letters=False)
    assert row["checklist_precision"] < 1.0 or row["checklist_recall"] < 1.0


def test_judge_reference_marks_separate_good_and_damaged_letters():
    items = judge.build_validation_set()
    genuine = [i for i in items if i["kind"] == "genuine"]
    assert genuine and all(sum(judge.reference_marks(i["letter"], i["facts"]).values()) == 5 for i in genuine)
    for kind, crit in (("drop_doc", "documents"), ("wrong_name", "asset_claimant"), ("invent", "no_invented"),
                       ("invent_date", "no_invented"), ("informal", "formal")):
        damaged = [i for i in items if i["kind"] == kind]
        assert damaged and all(judge.reference_marks(i["letter"], i["facts"])[crit] == 0 for i in damaged)


def test_kappa_basics():
    assert judge.kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert judge.kappa([1, 0, 1, 0], [0, 1, 0, 1]) == -1.0


def test_score_case_counts_wrong_person_and_questions():
    key = {"assets": [{"record_id": "B001", "status": "MISSING_ITEMS", "required_docs": ["DOC_DEATH_CERT"], "missing": []}],
           "expected_questions": ["B001"], "doc_conflict": False, "expect_tool_error": False}
    packs = {"bank_deposit:B001": {"status": "MISSING_ITEMS", "requirements": [{"doc_code": "DOC_DEATH_CERT", "rule_id": "BANK-LH-01", "have_it": True}]},
             "bank_deposit:B009": {"status": "MISSING_ITEMS", "requirements": [{"doc_code": "DOC_DEATH_CERT", "rule_id": "BANK-LH-01", "have_it": True}]}}
    s = score_case(packs, key, retrieval.rule_exists, asked=["B001", "B009"], state={})
    assert s["wrong_person_matches"] == 1 and s["question_precision"] == 0.5 and s["question_recall"] == 1.0
    assert s["checklist_precision"] == 0.5          # the wrong asset's documents count as false positives
