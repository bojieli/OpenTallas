"""R21: pair_unc exporter = ONE variation model per segment (OWNER 10-27 shared model).
The mesh MC term covers die input -> fine-mesh tap node only; the AOCV random/distance terms cover only the segments
below the tap node (tap buffer + tap->entry stub + core tree).  So: MC samples move only mesh_uncertainty_ps; the
AOCV terms move only with the below-tap stub / core; moving the two tap NODES along the mesh (the MC-covered segment,
same stub) changes no AOCV term except the bbox distance factor; and the guard refuses an MC that absorbed the stub."""
import json
from pathlib import Path

import pytest
import qc_clk_mesh3 as M

AOCV = json.loads((Path(M.__file__).resolve().parent / "clk_aocv_table.json").read_text())["clock_aocv"]


def _tap(x, stub=100.0):
    return dict(tap=(x, 0.0), entry=(x, stub), stub_um=stub)


def _u(tap, samples, g=0.0021):
    M.pair_u.mc_includes_stub = False
    return M.pair_u("a", "b", tap, {"TT": samples, "FF": samples}, AOCV, g)


def test_mc_samples_move_only_the_mesh_term():
    tap = {"a": _tap(0.0), "b": _tap(500.0)}
    r1 = _u(tap, [{"tap_arr_ps": {"a": 100.0, "b": 101.0}}])
    r2 = _u(tap, [{"tap_arr_ps": {"a": 100.0, "b": 140.0}}, {"tap_arr_ps": {"a": 100.0, "b": 90.0}}])
    for c in ("TT", "FF"):
        assert r1[c]["aocv_random_ps"] == r2[c]["aocv_random_ps"]
        assert r1[c]["aocv_distance_ps"] == r2[c]["aocv_distance_ps"]
        assert r1[c]["mesh_uncertainty_ps"] == 1.0 and r2[c]["mesh_uncertainty_ps"] == 40.0
        assert r2[c]["total_ps"] == pytest.approx(r2[c]["aocv_random_ps"] + r2[c]["aocv_distance_ps"] + 40.0, abs=2e-3)


def test_aocv_prices_only_below_the_tap_node():
    near = _u({"a": _tap(0.0), "b": _tap(500.0)}, [{"tap_arr_ps": {"a": 0.0, "b": 0.0}}])
    far = _u({"a": _tap(0.0), "b": _tap(5000.0)}, [{"tap_arr_ps": {"a": 0.0, "b": 0.0}}])
    longstub = _u({"a": _tap(0.0, 900.0), "b": _tap(500.0, 900.0)}, [{"tap_arr_ps": {"a": 0.0, "b": 0.0}}])
    for c in ("TT", "FF"):
        # tap-node distance (mesh segment) does not add AOCV stages or unshared delay ...
        assert far[c]["aocv_random_ps"] == near[c]["aocv_random_ps"]
        assert far[c]["noncommon_ps"] == near[c]["noncommon_ps"]
        # ... it scales only the g x bbox factor applied to the below-tap unshared delay
        assert far[c]["aocv_distance_ps"] == pytest.approx(
            near[c]["aocv_distance_ps"] * far["bbox_diag_mm"] / near["bbox_diag_mm"], rel=5e-3)
        # a longer below-tap stub adds AOCV stages / unshared delay
        assert longstub[c]["aocv_random_ps"] > near[c]["aocv_random_ps"]
        assert longstub[c]["noncommon_ps"] > near[c]["noncommon_ps"]
    assert near["var_model"]["overlap_stages"] == 0


def test_guard_refuses_mc_that_includes_the_stub():
    tap = {"a": _tap(0.0), "b": _tap(500.0)}
    M.pair_u.mc_includes_stub = True
    try:
        with pytest.raises(AssertionError):
            M.pair_u("a", "b", tap, {"TT": [{"tap_arr_ps": {"a": 0.0, "b": 0.0}}],
                                     "FF": [{"tap_arr_ps": {"a": 0.0, "b": 0.0}}]}, AOCV, 0.0021)
    finally:
        M.pair_u.mc_includes_stub = False
