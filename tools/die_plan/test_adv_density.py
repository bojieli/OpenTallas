"""pytest: ADV-DENSITY on a fixture modeled on the real positive (FLOW-STRIPBODY-R2 11-22: S81 lepe_mu_C t1 strip_S,
1442.88 x 43.2, 56,543 synth cells, 0.907 cells/um2, place FAIL at OT_CLAND; lane fix = strip_S height 95.04)."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_density as A  # noqa: E402

STRIP = "dsdv_slice_lepe_mu_C__t1__strip_S"
BODY = "dsdv_slice_lepe_mu_C__t1"


def plan(strip_h=43.2):
    bands = {"leafup_i3": {"rect_um": [83.1167, 17.28, 294.2873, 43.2]},
             "leafup_i4": {"rect_um": [400.0, 17.28, 611.17, 43.2]},
             "xring_i0": {"rect_um": [700.0, 20.0, 920.0, 43.2]}}
    return {"die": {"name": "s81", "grid_um": 8.64},
            "partition_types": {
                STRIP: {"outline_um": [1442.88, strip_h], "hard": False, "hard_cores": [],
                        "clock": {"landing_contract": {"bands": bands}}},
                BODY: {"outline_um": [1442.88, 1140.48], "hard": False,
                       "hard_cores": [{"inst": "u_c.u_cap", "origin_um": [51.84, 717.12 - 43.2], "outline_um": [336.96, 414.72]},
                                      {"inst": "u_c.u_xr", "origin_um": [466.56, 950.4 - 43.2], "outline_um": [207.36, 164.16]}],
                       "clock": {}}},
            "partitions": [{"name": "s_7N_C__strip_S", "type": STRIP}, {"name": "s_7N_C", "type": BODY}]}


def cache(strip_rec=None):
    return {"made": "fixture", "cells": {"s81": {
        STRIP: {"last": strip_rec or {"cells": 56543, "t0": 1795360000, "stage": "place", "verdict": "FAIL",
                                      "soft_um2": 62332.4}},
        BODY: {"last": {"cells": 281576, "t0": 1795360000, "stage": "geom", "verdict": "PASS", "soft_um2": 1449000.0},
               "placed": {"cells": 281576, "t0": 1795360000, "stage": "geom", "verdict": "PASS", "soft_um2": 1449000.0}}}}}


def hits(lines, tn):
    return [ln for ln in lines if ln.startswith(f"WARN ADV-DENSITY {tn}:")]


def test_real_positive_strip_s_flagged():
    out = A.findings(plan(), "plan_c.json", None, cells_cache=cache())
    h = hits(out, STRIP)
    assert len(h) == 1, out
    assert "56,543 synth cells" in h[0] and "0.907 cells/um2 >= 0.6" in h[0]
    assert "height >= 95.04 um" in h[0]          # the lane's own J9 row (STRIP-S-HEIGHT 43.2 -> 95.04)
    assert "landing bands reserve" in h[0]
    assert not hits(out, BODY)
    assert out[-1].startswith("WARN ADV-DENSITY summary: 1 types")


def test_fixed_height_not_flagged():
    out = A.findings(plan(95.04), "plan_c.json", None, cells_cache=cache())
    assert not hits(out, STRIP), out           # 56,543 / 137,111 um2 = 0.41


def test_placed_evidence_suppresses():
    # a QC-hc-like type: dense, but its own kit placed at >= this density on the same soft area
    rec = {"cells": 56543, "t0": 1, "stage": "geom", "verdict": "PASS", "soft_um2": 62332.4}
    c = cache(rec)
    c["cells"]["s81"][STRIP]["placed"] = dict(rec)
    out = A.findings(plan(), "plan_c.json", None, cells_cache=c)
    assert not hits(out, STRIP)
    assert "1 dense but placed before" in out[-1]


def test_base_type_and_region_and_robustness():
    p = plan()
    p["partition_types"][STRIP + "__cl0123abcd"] = copy.deepcopy(p["partition_types"][STRIP])
    p["partitions"].append({"name": "x", "type": STRIP + "__cl0123abcd"})
    p["partition_types"][BODY]["place_regions"] = [{"name": "xg_ring_router", "util": 0.7}]
    out = A.findings(p, "plan_c.json", None, cells_cache=cache())
    assert hits(out, STRIP + "__cl0123abcd") and "base kit" in hits(out, STRIP + "__cl0123abcd")[0]
    assert any("place_regions xg_ring_router util 0.7" in ln for ln in hits(out, BODY))
    assert A.findings({"partition_types": {"x": {"outline_um": "bad"}}, "partitions": [{"type": "x"}]}, "p", None,
                      cells_cache=cache())[-1].startswith("WARN ADV-DENSITY")
    assert A.findings(None, "p")[0].startswith("WARN ADV-DENSITY not checked")


def test_no_cache_is_one_line(tmp_path, monkeypatch):
    monkeypatch.setenv(A.CACHE_ENV, str(tmp_path / "missing.json"))
    monkeypatch.setattr(A, "CACHE_DEFAULTS", (str(tmp_path / "a.json"), str(tmp_path / "b.json")))
    out = A.findings(plan(), "plan_c.json", None)
    assert len(out) == 1 and "not checked" in out[0]
