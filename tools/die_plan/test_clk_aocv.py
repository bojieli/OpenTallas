"""CLK-AOCV (12.4a b1 DRAFT): table math, shared droop, flat reproduction, die_sta_related opt-in hook."""
import copy
import json
import math
from pathlib import Path

import clk_aocv as A
import die_sta_related as R

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "die_ci_margins.json").read_text())


def _T(rho=(), g=0.0):
    c = dict(mu_cell_ps=50.0, mu_stage_ps=100.0, cell_share=0.5, s_cell=0.04, rho=list(rho))
    return dict(schema=A.SCHEMA, k_sigma=3.0, classes=dict(A=dict(TT=c, FF=c), B=dict(TT=c, FF=c)),
                systematic=dict(g_per_mm=g), droop=dict(one_sided_late_frac=0.0511),
                net_flat=dict(late=1.03, early=0.97))


def test_random_part_averages_as_inverse_sqrt_depth():
    T = _T()
    r1, r16 = A.random_frac(T, "TT", {"A": 1}), A.random_frac(T, "TT", {"A": 16})
    assert math.isclose(r1, 0.12) and math.isclose(r16, 0.12 / 4)
    # positive stage correlation averages less
    assert A.random_frac(_T(rho=(0.2,)), "TT", {"A": 16}) > r16


def test_distance_term_linear_and_split_per_side():
    T = _T(g=0.004)
    lo, hi = A.cell_derate(T, "TT", {"A": 16}, 0.0), A.cell_derate(T, "TT", {"A": 16}, 10000.0)
    assert math.isclose(hi[0] - lo[0], 0.004 * 10 / 2) and math.isclose(lo[1] - hi[1], 0.02)


def test_shared_droop_zero_in_one_region_full_across():
    T = _T()
    br = dict(cell_ps=1000.0, net_ps=0.0, stages={"A": 16})
    same = A.branch_pessimism(T, "TT", br, br, 0.0, True, "setup")
    diff = A.branch_pessimism(T, "TT", br, br, 0.0, False, "setup")
    assert math.isclose(diff - same, 0.0511 * 1000.0)
    assert math.isclose(same, 2 * 1000.0 * 0.03)


def test_flat_reproduces_qc_mp_region_die_root():
    # QC-MP-REGION die_root TT: nc 6297.261, fc = 52.713/(52.713+0.058822*450) on one branch, both sides equal
    nc = 6297.261
    fc = 52.713 / (52.713 + 0.058822 * 450.0)
    br = dict(cell_ps=fc * nc, net_ps=(1 - fc) * nc, stages={"A": 1})
    assert abs(A.flat_pessimism(M, br, br, "setup", False, False) - 759.322) < 0.5
    # shared droop has no effect across regions, removes the IR share inside one region
    assert A.flat_pessimism(M, br, br, "setup", False, True) == A.flat_pessimism(M, br, br, "setup", False, False)
    assert abs(A.flat_pessimism(M, br, br, "setup", True, False) - A.flat_pessimism(M, br, br, "setup", True, True)
               - 0.0511 * fc * nc) < 1e-6


def test_draft_table_file_loads_and_is_monotonic():
    T = A.load(HERE / "clk_aocv_table.json")
    assert T["status"].startswith("DRAFT")
    for cls in T["classes"]:
        for c in T["classes"][cls]:
            v = [A.random_frac(T, c, {cls: n}) for n in (1, 4, 16, 64)]
            assert v == sorted(v, reverse=True) and v[0] > 0


def _taps():
    return {"a": dict(late_ps=1000.0, early_ps=990.0, cppr_node="h0", stages_from_root=10, xy_um=[0, 0]),
            "b": dict(late_ps=1050.0, early_ps=1040.0, cppr_node="h0", stages_from_root=10, xy_um=[100, 0])}


REG = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=46.5, setup_ps=5.6, hold_ps=22.2)


def test_die_sta_related_default_unchanged_and_hook_subtracts(tmp_path):
    taps, rng = _taps(), {"h0": 10.0, "h": 30.0}
    pairs = [("a", "b", "p")]
    base = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0)
    assert "clock_ocv_pessimism_max_ps" not in base
    t = tmp_path / "t.json"
    t.write_text(json.dumps(dict(clock_aocv=_T(g=0.004))))
    meta = dict(corner="TT", node_stages={"h0": 4, "h": 0}, node_xy_um={"h0": [50, 50], "h": [0, 0]},
                spine_late={"h0": 400.0, "h": 0.0}, spine_early={"h0": 395.0, "h": 0.0})
    fn = R.clock_ocv_fn("table", "shared", meta, taps, 250.0, t)
    r = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, ocv=fn)
    p = r["clock_ocv_pessimism_max_ps"]
    assert p["setup"] > 0 and math.isclose(r["worst_setup_slack_ps"], round(base["worst_setup_slack_ps"] - p["setup"], 2),
                                           abs_tol=0.02)
    assert math.isclose(r["worst_hold_slack_ps"], round(base["worst_hold_slack_ps"] - p["hold"], 2), abs_tol=0.02)
    # flat mode with stated droop is larger than table+shared here (same region, short branches)
    ff = R.clock_ocv_fn("flat", "stated", meta, taps, 250.0, t)
    assert ff("a", "b", "setup") > fn("a", "b", "setup")


def test_hook_refuses_without_fold_fields(tmp_path):
    t = tmp_path / "t.json"
    t.write_text(json.dumps(dict(clock_aocv=_T())))
    taps = {"a": dict(late_ps=1.0, early_ps=1.0, cppr_node="h")}
    try:
        R.clock_ocv_fn("table", "shared", dict(corner="TT"), taps, 250.0, t)
    except SystemExit as e:
        assert "fold export" in str(e)
    else:
        raise AssertionError("must refuse")
