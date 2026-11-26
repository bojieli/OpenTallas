"""tests of leg405_stage_seats.py and the LEG405-STAGED check (C-LEG405-R2)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as F  # noqa: E402
import leg405_stage_seats as L  # noqa: E402


def plan(path_um, D, se=0, note=None):
    r = {"inst": "u_x", "port": "o", "path_um": path_um, "stages_existing": se, "D": D}
    if note:
        r["note"] = note
    return {"partition_types": {"T": {"relay_depth": [r]}}}


def flagged(raw):
    return [x for x in F.findings_by_check["LEG405-STAGED"](raw, "p.json") if "summary" not in x]


def test_staged_rows_are_not_flagged_but_zero_still_is():
    r = plan(700.0, 1)
    assert flagged(r) == []
    assert [x for x in F.findings_by_check["LEG405-ZERO"](r, "p.json") if "summary" not in x]


def test_understaged_row_is_flagged_and_restaged():
    r = plan(898.5, 1)
    assert "short 1 station" in flagged(r)[0]
    rep = L.restage(r)
    assert r["partition_types"]["T"]["relay_depth"][0]["D"] == 2 and rep["extra_cycles_total"] == 1
    assert flagged(r) == []


def test_existing_stage_credit_exact_boundary_and_never_lowers():
    r = plan(810.0, 0, se=1)           # 810 = 2 x 405: one station, already there
    assert flagged(r) == [] and L.restage(r)["latency"] == []
    r = plan(300.0, 3)
    L.restage(r)
    assert r["partition_types"]["T"]["relay_depth"][0]["D"] == 3


def test_align_rows_reported():
    r = plan(1300.0, 1, note="align cc with x branch D=1")
    rep = L.restage(copy.deepcopy(r))
    assert len(rep["align_review"]) == 1 and rep["latency"][0]["new_D"] == 3
