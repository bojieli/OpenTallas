"""QC-SLICECLK-2 10-27: G0C 'no cell estimate' on clock-landing cohort types (QC 24, KV 20) is fixed in cells.estimate."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cells as CE  # noqa: E402


def _band(w):
    return {"width": w, "rect_um": [0, 0, 1, 1]}


def _plan():
    lc = {"bands": {"a_wi": _band(116), "b_wi": _band(520)}}
    return {"partitions": [{"name": "p0", "type": "base"}, {"name": "p1", "type": "base__cl0011aabb"},
                           {"name": "p2", "type": "own"}, {"name": "p3", "type": "phy"},
                           {"name": "p4", "type": "orphan__cl99"}],
            "partition_types": {
                "base": {"contents": [{"module": "m", "cells": 1000}]},
                "base__cl0011aabb": {"contents": [{"module": "m"}], "landing_base_type": "base",
                                     "clock": {"landing_contract": lc}},
                "own": {"cells": 5000, "clock": {"landing_contract": lc}},
                "phy": {"hard": True, "landing_base_type": "base"},
                "orphan__cl99": {"landing_base_type": "missing"}}}


def test_ring_cells_matches_land_kv_model():
    assert CE.ring_cells(0) == 4 * 4 + 124 + 612
    assert CE.ring_cells(63) == 4 * 67 + 124 + 612
    assert CE.ring_cells(64) == 4 * 68 + 124 + 2 * 612


def test_cohort_inherits_base_plus_rings():
    est, _ = CE.estimate(_plan(), None, (), auto=False)
    rings = CE.ring_cells(116) + CE.ring_cells(520)
    assert est["base"] == (1000, "contents")
    c, basis = est["base__cl0011aabb"]
    assert c == 1000 + rings and basis.startswith("landing cohort of base")


def test_plan_cells_complete_hard_and_unknown_base():
    est, _ = CE.estimate(_plan(), None, (), auto=False)
    assert est["own"] == (5000, "plan")          # type.cells already counts its rings
    assert "phy" not in est                      # hard IP needs no estimate
    assert "orphan__cl99" not in est             # unknown base stays missing (G0C still errors)


def test_no_landing_unchanged():
    raw = _plan()
    for t in raw["partition_types"].values():
        t.pop("landing_base_type", None)
        (t.get("clock") or {}).pop("landing_contract", None)
    est, _ = CE.estimate(raw, None, (), auto=False)
    assert set(est) == {"base", "own"} and est["base"] == (1000, "contents")


def test_base_type_left_plan_uses_by_type_evidence():
    """QC slice form: every cbn_q00 instance moved to cohorts, so cbn_q00 is no longer a plan type; its by_type row
    in plan_notes.json (cells_per_type) must still reach the cohorts (the 24 G0C 'no cell estimate' errors)."""
    import json
    import tempfile
    raw = _plan()
    del raw["partition_types"]["base"]
    raw["partitions"] = [p for p in raw["partitions"] if p["type"] != "base"]
    raw["partition_types"]["base__cl0011aabb"]["contents"] = [{"module": "m"}]
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "plan_notes.json"
        f.write_text(json.dumps({"cells_per_type": {"base": {"cells": 782764}, "other": 7}}))
        est, used = CE.estimate(raw, d, ())
    rings = CE.ring_cells(116) + CE.ring_cells(520)
    c, basis = est["base__cl0011aabb"]
    assert c == 782764 + rings and "by_type plan_notes.json" in basis
    assert "base" not in est and "other" not in est     # only plan types are reported
