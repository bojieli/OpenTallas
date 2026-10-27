"""INFRA-FIRST-HEAD-5: bump-pad source model + measured per-core power map."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import die_trial as D  # noqa: E402
import head_pg_sweep as H  # noqa: E402


def test_point_bump_unchanged_by_default():
    a = D.bumps_tcl(None, [("VDD", 75, 75), ("VSS", 225, 75)])
    assert a == D.bumps_tcl(None, [("VDD", 75, 75), ("VSS", 225, 75)], pad_um=0.0)
    assert "ot_pad" not in a and "OT_BUMPS actual_m9_sources 2" in a


def test_pad_bumps_one_term_per_bump_all_overlaps():
    t = D.bumps_tcl(None, [("VDD", 75, 75), ("VSS", 225, 75)], pad_um=75)
    assert t.count("\not_pad ") == 2 and "ot_pad VDD 0 75 75" in t and "ot_pad VSS 1 225 75" in t
    assert "set pad_half [expr {round(75*$bump_dbu/2.0)}]" in t
    assert "pad_fallback" in t and "lappend hits" in t      # every same-net strap under the pad, fallback counted


def _plan():
    return dict(partition_types={
        "hd_tile": {"outline_um": [100.0, 100.0], "hard_cores": [
            {"module": "ot_s81hd_elemA_cv", "origin_um": [0.0, 0.0], "outline_um": [50.0, 50.0]},
            {"module": "ot_s81hd_elemB_cv", "origin_um": [50.0, 50.0], "outline_um": [40.0, 40.0]}]},
        "hd_spn": {"outline_um": [10.0, 100.0]}},
        partitions=[{"name": "t0", "type": "hd_tile", "origin_um": [0.0, 0.0], "orient": "R0"},
                    {"name": "t1", "type": "hd_tile", "origin_um": [100.0, 0.0], "orient": "MY"},
                    {"name": "s", "type": "hd_spn", "origin_um": [200.0, 0.0], "orient": "R0"}])


def _pw():
    return {"activities": {"meas": {"cores": {"elemA": {"total_w": 0.003}, "elemB": {"total_w": 0.004}},
                                    "tile_w_upper": 0.012, "tile_w_mm2_upper": 1.2, "tile_w_mm2_lower": 0.7}}}


def _watts(loads, rect):
    ov = lambda a, b: max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return sum(d * ov(r, rect) for r, d in loads) * 1e-6


def test_core_map_preserves_watts_and_mirrors():
    loads, info = H.core_map(_plan(), _pw(), "meas")
    assert abs(_watts(loads, [0, 0, 100, 100]) - 0.012) < 1e-12           # tile upper watts
    assert abs(_watts(loads, [0, 0, 50, 50]) - 0.003) < 1e-12             # elemA on its plan outline
    assert abs(_watts(loads, [50, 50, 90, 90]) - 0.004) < 1e-12           # elemB hotspot
    assert abs(_watts(loads, [150, 0, 200, 50]) - 0.003) < 1e-12          # MY tile: elemA mirrored to the right
    assert abs(_watts(loads, [110, 50, 150, 90]) - 0.004) < 1e-12
    assert abs(_watts(loads, [200, 0, 210, 100]) - 1.2 * 0.001) < 1e-12   # other types at the tile upper density
    assert info["core_w_mm2"]["elemB"] == 2.5
    lo, _ = H.core_map(_plan(), _pw(), "meas", "lower")
    assert abs(_watts(lo, [0, 0, 100, 100]) - 0.007) < 1e-12              # lower bound: glue 0 W
