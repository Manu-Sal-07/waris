"""Benchmark tests: the 60-case generator, proof documents and OCR intake, the documents-first pipeline, letters, baseline,
ablations, judge and metrics.

Scenario tests rebuild each case FROM ITS PROOF FILES by OCR (exactly what a family upload does) and run the real graph with the
LLM switched off (fixed fallbacks), so they are deterministic; set WARIS_TEST_ALL=1 to run all 60 cases.
"""
import json
import os
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from data import generate_cases as gen
from eval import judge, run_eval
from eval.metrics import score_case
from waris import baseline, config, intake, llm
from waris.agents import letters
from waris.guardrails import validate_case_input
from waris.tools import ocr, portals, retrieval

IDX = json.loads((config.CASES_DIR / "index.json").read_text(encoding="utf-8"))
SPLIT = json.loads((config.CASES_DIR / "split.json").read_text(encoding="utf-8"))
FOLDER = {c["case_id"]: config.ROOT / "demo_proofs" / c["folder"] for c in IDX}
CATALOGUE = ["clean", "name_initials", "name_spelling", "name_translit", "name_order", "name_maiden", "namesake",
             "namesake_ambiguous", "partial_info", "no_assets", "multi_account", "claimant_nominee", "claimant_legal_heir",
             "amount_small", "amount_large", "joint_account", "docs_missing", "doc_conflict", "no_rule", "later_session",
             "scan_clean", "scan_rotated", "scan_blurry", "scan_faded", "scan_inject", "tool_fault"]


def truth(cid):
    d = config.CASES_DIR / cid
    return (json.loads((d / "input.json").read_text(encoding="utf-8")), json.loads((d / "answer_key.json").read_text(encoding="utf-8")))


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
    llm.set_enabled(True)
    config.ABLATE.clear()
    mp.undo()


# ---------------------------------------------------------------- data generator
def test_generator_is_deterministic():
    r = next(r for r in gen.recipes() if r.id == "h01")
    a, b = gen.build_case(r), gen.build_case(r)
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


def test_proof_folders_are_named_after_the_deceased_and_difficulty():
    for c in IDX:
        d, _ = truth(c["case_id"])
        assert c["folder"] == gen._slug(d["deceased"]["name"]) + "_" + c["difficulty"]
        assert FOLDER[c["case_id"]].is_dir() and (FOLDER[c["case_id"]] / "README.txt").exists()
    assert (config.ROOT / "demo_proofs" / "ramaswamy_subramanian_demo" / "01_death_certificate.png").exists()
    assert len({c["folder"] for c in IDX}) == 60


def test_one_shared_portal_database_holds_every_family():
    import sqlite3
    con = sqlite3.connect(config.PORTAL_DB)
    ids = [r[0] for t in ("bank", "insurer", "registry") for r in con.execute(f"select record_id from {t}")]
    assert len(ids) == len(set(ids)) and len(ids) > 300
    for cid in ("e01", "h07", "m22"):                    # each case's true record is in the shared database under its global id
        _, key = truth(cid)
        for a in key["assets"]:
            assert a["record_id"] in ids


def test_inputs_validate_and_keys_are_consistent():
    for c in IDX:
        case, key = truth(c["case_id"])
        validate_case_input({k: case[k] for k in ("case_id", "deceased", "claimant", "scans")})
        for a in key["assets"]:
            assert set(a["missing"]) <= set(a["required_docs"])
            if a["status"] == "READY":
                assert not a["missing"]
            if a["status"] == "MISSING_ITEMS":
                assert a["missing"]
        for rel in key.get("later_files", []):
            assert (FOLDER[c["case_id"]] / rel).exists()


def test_generator_rows_follow_the_identity_policy():
    r = next(r for r in gen.recipes() if r.id == "h05")
    assert gen.validate_rows(gen.build_case(r), []) == []


# ---------------------------------------------------------------- OCR and intake
def test_ocr_reads_clean_and_rotated_proofs_and_refuses_blurry_ones():
    ok = ocr.read_scan(FOLDER["e11"] / "01_death_certificate.png")
    assert ok["readable"] and ok["doc_code"] == "DOC_DEATH_CERT" and ok["entities"]["deceased_dod"]
    assert ocr.read_scan(FOLDER["e14"] / "01_death_certificate.png")["readable"]                       # rotated
    assert not ocr.read_scan(FOLDER["h13"] / "01_death_certificate.png")["readable"]                   # blurry
    assert ocr.read_scan(FOLDER["e01"] / "03_relationship_proof.png")["doc_code"] == "DOC_RELATIONSHIP_PROOF"


def test_case_is_built_from_the_uploaded_documents():
    truth_input, key = truth("e01")
    b = intake.build_case(intake.list_proofs(FOLDER["e01"]), key["form"])
    c = b["case"]
    assert b["needs"] == [] and all(b["essentials"].values())
    assert c["deceased"]["name"] == truth_input["deceased"]["name"] and c["deceased"]["dob"] == truth_input["deceased"]["dob"]
    assert c["deceased"]["dod"] == truth_input["deceased"]["dod"] and c["deceased"]["city"] == truth_input["deceased"]["city"]
    assert c["claimant"]["name"] == truth_input["claimant"]["name"] and c["claimant"]["relationship"] == truth_input["claimant"]["relationship"]
    assert c["claimant"]["claimant_type"] == "legal_heir" and c["claim_for"] == ["bank"]
    assert b["sources"]["deceased_name"].startswith("read from the death certificate")
    assert intake.case_id_for(c["deceased"]["name"], c["deceased"]["dob"], c["deceased"]["dod"]) == c["case_id"]


def test_maiden_name_comes_from_the_death_certificate_and_form_fields_are_respected():
    _, key = truth("m12")
    b = intake.build_case(intake.list_proofs(FOLDER["m12"]), {**key["form"], "claiming_as": "nominee", "other_names": "Savitri Rao, Savi"})
    assert b["case"]["deceased"]["aliases"][0] in truth("m12")[0]["deceased"]["aliases"]          # 'Also known as' line on the certificate
    assert {"Savitri Rao", "Savi"} <= set(b["case"]["deceased"]["aliases"])                         # typed in the form
    assert b["case"]["claimant"]["claimant_type"] == "nominee" and b["case"]["claimant"]["has_nomination"]


def test_unreadable_death_certificate_falls_back_to_what_the_family_types():
    d, key = truth("h13")                                                       # the death certificate is blurry
    paths = intake.list_proofs(FOLDER["h13"])
    no_help = intake.build_case(paths, key["form"])
    assert no_help["essentials"]["death_certificate"] is False
    assert no_help["case"] is not None and no_help["case"]["deceased"]["name"] == d["deceased"]["name"]    # the relationship proof names the deceased
    assert no_help["case"]["deceased"]["dod"] is None                                                        # but only the certificate has the date of death
    typed = intake.build_case(paths, key["form"], fallback={"deceased_dod": d["deceased"]["dod"]})
    assert typed["case"]["deceased"]["dod"] == d["deceased"]["dod"] and typed["sources"]["deceased_dod"].startswith("typed")


def test_missing_essentials_are_listed_and_a_typed_value_wins():
    b = intake.build_case([], {})
    assert b["case"] is None and any("deceased" in n for n in b["needs"]) and any("claimant" in n for n in b["needs"])
    c = intake.build_case(intake.list_proofs(FOLDER["e01"]), {}, override={"deceased_name": "Typed Name", "relationship": "nephew"})
    assert c["case"]["deceased"]["name"] == "Typed Name" and c["case"]["claimant"]["relationship"] == "nephew"


# ---------------------------------------------------------------- scenarios, end to end (documents first)
REPRESENTATIVE = ["e01", "e04", "e11", "m01", "m03", "m07", "m10", "m12", "m15", "m18", "m22", "m23", "m25", "h01", "h04", "h05",
                  "h07", "h10", "h12", "h13", "h14", "h16", "h18", "h19", "h20"]
CASES = [c["case_id"] for c in IDX] if os.getenv("WARIS_TEST_ALL") else REPRESENTATIVE


@pytest.mark.parametrize("cid", CASES)
def test_scenario_matches_answer_key(cid, tmp_path):
    row = run_eval.run_one(cid, "full_nollm", 0, tmp_path, save_letters=False)
    assert row["ex_ok"] == row["ex_n"], row["ex_failed"]                    # OCR rebuilt exactly the case the generator started from
    assert row["status_accuracy"] == 1.0, row["detail"]
    assert row["wrong_person_matches"] == 0
    assert row["abstention_correct"] and row["conflict_ok"] and row["tool_error_ok"]
    assert row["checklist_precision"] == 1.0 and row["checklist_recall"] == 1.0
    assert row["citation_coverage"] == 1.0
    assert row["question_precision"] == 1.0 and row["question_recall"] == 1.0
    assert row["reasked_in_session2"] == 0


def test_injection_in_a_proof_is_flagged_and_does_not_change_the_result(tmp_path):
    row = run_eval.run_one("h13", "full_nollm", 0, tmp_path, save_letters=False)
    assert row["injection_flagged"] and row["status_accuracy"] == 1.0


def test_namesake_and_ambiguous_record_are_never_claimed(tmp_path):
    for cid in ("h01", "h04", "h12"):
        assert run_eval.run_one(cid, "full_nollm", 0, tmp_path, save_letters=False)["wrong_person_matches"] == 0


def test_no_assets_case_claims_nothing(tmp_path):
    row = run_eval.run_one("m18", "full_nollm", 0, tmp_path, save_letters=False)
    assert row["statuses"] == {} and row["n_truth"] == 0 and row["wrong_person_matches"] == 0


def test_only_the_selected_institutions_are_searched(tmp_path):
    d, key = truth("e01")
    b = intake.build_case(intake.list_proofs(FOLDER["e01"]), {**key["form"], "claim_for": ["insurer"]})
    assert b["case"]["claim_for"] == ["insurer"]
    row = run_eval.run_one("e01", "full_nollm", 0, tmp_path, save_letters=False)
    assert row["tool_calls"] == 1                                            # e01 asks about banks only


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
    config.LETTER_LLM = False
    for cid, n in (("e04", 1), ("h10", 1)):                       # h10: one asset abstained -> no letter for it
        row = run_eval.run_one(cid, "full_nollm", 0, tmp_path, save_letters=False)
        assert row["letters"] == n


# ---------------------------------------------------------------- baseline, ablations, judge, metrics
def test_baseline_trusts_the_top_rule_without_grading():
    llm.disable()
    _, key = truth("e04")
    b = intake.build_case(intake.list_proofs(FOLDER["e04"]), key["form"])
    state = baseline.run_baseline(b["case"])
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
