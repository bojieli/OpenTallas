"""P-DRC-DECK-BASELINE: every hard-core category gates; only V4.M5.AUX.2 outside the hard-core zone is excluded, and then the verdict is PASS-PROVISIONAL."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merged_gds_drc as M


@pytest.mark.parametrize("cat", ["M4.AUX.3", "M5.AUX.3", "V4.AUX.1", "V5.AUX.1", "V3.M4.AUX.2", "V4.M5.AUX.2", "V5.M6.AUX.2", "V3.W.1", "M3.S.6"])
def test_hardcore_marker_of_any_category_fails(cat):
    v = M.judge(dict(new_hardcore=3, per_category={"'%s'" % cat: {"HARDCORE": 3}}), {})
    assert v["verdict"] == "FAIL" and v["new_hardcore"] == 3 and v["gating_categories"] == {cat: 3}


def test_parent_zone_v4_m5_aux_is_excluded_but_provisional():
    v = M.judge(dict(new_hardcore=0, per_category={"'V4.M5.AUX.2'": {"PARENT": 1669570}}), {})
    assert v["verdict"] == "PASS-PROVISIONAL" and v["provisional"] and v["excluded_outside_hardcore"] == {"V4.M5.AUX.2": 1669570}


def test_other_parent_zone_categories_are_not_excluded_by_name():
    v = M.judge(dict(new_hardcore=0, per_category={"'M4.AUX.3'": {"PARENT": 5}}), {})
    assert v["verdict"] == "PASS" and not v["provisional"]       # PARENT markers never gate; nothing was excluded


def test_clean_is_pass_and_old_compare_keeps_the_raw_count():
    assert M.judge(dict(new_hardcore=0, per_category={}), {})["verdict"] == "PASS"
    assert M.judge(dict(new_hardcore=3), {})["verdict"] == "FAIL"


def test_gate_check_reads_provisional_as_not_run(tmp_path, monkeypatch):
    import json
    kit = tmp_path
    (kit / "merged_gds_drc").mkdir()
    (kit / "merged_gds_drc" / "verdict.json").write_text(json.dumps(dict(verdict="PASS-PROVISIONAL")))
    monkeypatch.setattr(M, "kit_plan", lambda k: dict(required=True, gated=["x.lef"]))
    assert M.gate_check(str(kit))["verdict"] == "NOT RUN"
