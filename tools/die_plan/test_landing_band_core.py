"""FLOW-FLEET-R1 11-22 (lever 7): G0 landing band x core overlap is an ERROR (S81 kv_leaf t5: vp cores regridded onto ft0_i / ft1_i / monitor_0)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_band_core as LB  # noqa: E402
import check as CK  # noqa: E402

T5 = {"clock": {"landing_contract": {
    "bands": {"ft0_i": {"rect_um": [65.28, 1168.56, 125.348, 1209.6], "width": 8},
              "ft1_i": {"rect_um": [126.528, 1168.56, 186.596, 1209.6], "width": 8},
              "monitor_0": {"rect_um": [180.36, 1140.48, 189, 1168.56]},
              "clear_i": {"rect_um": [400, 10, 420, 20]},
              "split_i": {"rects_um": [[0, 0, 10, 10], [500, 500, 510, 510]]}},
    "native_stage_groups": {"groups": [{"tag": "stage:a", "rect_um": [300, 300, 320, 320]}]},
    "group_rects_um": {"g1": [700, 700, 710, 710]}}}}
BOXES = {"u_lf.u_vp.g_ln[4].u_l": (43.308, 1105.96, 157.788, 1220.44), "u_lf.u_vp.g_ln[0].u_l": (181.548, 1105.96, 296.028, 1220.44),
         "edge": (420, 10, 440, 20), "stage_core": (310, 310, 400, 400), "grp": (705, 0, 800, 705.0), "far": (505, 505, 900, 900)}


def test_band_rects_kinds():
    k = {(kind, n) for kind, n, _ in LB.band_rects(T5)}
    assert ("band", "ft0_i") in k and ("band", "split_i#1") in k and ("stage_band", "stage:a") in k and ("group_band", "g1") in k


def test_t5_overlaps_and_shares():
    f = LB.findings_type("t5", T5, BOXES)
    got = {(x["band"], x["core"]): x["share"] for x in f}
    assert got[("ft0_i", "u_lf.u_vp.g_ln[4].u_l")] == 1.0
    assert abs(got[("ft1_i", "u_lf.u_vp.g_ln[4].u_l")] - 0.52) < 0.01
    assert abs(got[("monitor_0", "u_lf.u_vp.g_ln[0].u_l")] - 0.86) < 0.01
    assert ("clear_i", "edge") not in got                          # touching edges are legal
    assert ("stage:a", "stage_core") in got and ("split_i#1", "far") in got
    assert got[("g1", "grp")] == 0.25


def test_g0_error_class():
    class P:
        types = {"t5": T5, "clean": {"clock": {"landing_contract": {"bands": {"x": {"rect_um": [0, 0, 5, 5]}}}}}, "unused": T5}
        parts = {"p0": {"type": "t5"}, "p1": {"type": "clean"}}
    R = CK.Report()
    s = LB.check(P, R, boxes_fn=lambda t: BOXES if t is T5 else {"c": (5, 0, 9, 5)})
    errs = R.errors()
    assert errs and all(e["check"] == "landing_band_core" and e["type"] == "t5" for e in errs)
    assert s["types"] == 1 and s["findings"] == len(errs)
    assert any("ft0_i" in e["msg"] and "100 % of the band" in e["msg"] for e in errs)


def test_check_py_runs_it():
    src = (Path(__file__).resolve().parent / "check.py").read_text()
    assert 'summ["landing_band_core"] = LBC.check(P, R)' in src
