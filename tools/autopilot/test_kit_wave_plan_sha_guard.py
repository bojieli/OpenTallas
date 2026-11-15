"""WAVE-POR guard: kit_wave refuses a die whose plan file sha differs from dies.<die>.plan_sha256."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kit_wave as kw


def test_no_declared_sha_never_blocks():
    assert kw.plan_sha_mismatch({"plan": "/p.json"}, {"plan_sha": "a" * 64}) is None


def test_match_passes_and_case_ignored():
    assert kw.plan_sha_mismatch({"plan": "/p.json", "plan_sha256": "AB" * 32}, {"plan_sha": "ab" * 32}) is None


def test_mismatch_blocks_with_reason():
    why = kw.plan_sha_mismatch({"plan": "/p.json", "plan_sha256": "a" * 64}, {"plan_sha": "b" * 64})
    assert why.startswith("PLAN_SHA_MISMATCH") and "/p.json" in why and "bbbbbbbbbbbb" in why and "aaaaaaaaaaaa" in why


def test_unreadable_plan_left_to_existing_error_path():
    assert kw.plan_sha_mismatch({"plan": "/p.json", "plan_sha256": "a" * 64}, {"error": "x"}) is None
