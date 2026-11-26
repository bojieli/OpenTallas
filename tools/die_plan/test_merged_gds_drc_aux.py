"""P-DRC-DECK-BASELINE: *.AUX.* categories never gate the merged-GDS DRC."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merged_gds_drc as M


def test_aux_only_markers_pass_and_are_reported():
    cmp = dict(new_hardcore=26866, new_parent=5, per_category={"'V4.M5.AUX.2'": {"HARDCORE": 26866, "PARENT": 5}})
    v = M.judge(cmp, {})
    assert v["verdict"] == "PASS" and v["new_hardcore"] == 0 and v["ignored_aux_hardcore"] == 26866 and v["new_hardcore_raw"] == 26866


def test_real_categories_still_gate():
    cmp = dict(new_hardcore=30, per_category={"'M3.S.6'": {"HARDCORE": 7}, "'V4.M5.AUX.2'": {"HARDCORE": 23}})
    v = M.judge(cmp, {})
    assert v["verdict"] == "FAIL" and v["new_hardcore"] == 7 and v["gating_categories"] == {"M3.S.6": 7}


def test_old_compare_without_per_category_keeps_the_raw_count():
    assert M.judge(dict(new_hardcore=3), {})["verdict"] == "FAIL"
