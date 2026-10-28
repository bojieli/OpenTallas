"""LAND-HEAD-2: landed_phase_ocv (derated landed phase margin with the shared clk_aocv model)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import clk_aocv as CA  # noqa: E402
import landed_phase_ocv as LP  # noqa: E402


def _case(tmp_path):
    tree = {"taps": [{"port": "t_a__clk", "part": "a", "xy": [0, 0], "node": 1},
                     {"port": "t_b__clk", "part": "b", "xy": [1000, 0], "node": 2}],
            "node_buf": {"0": "b0", "1": "b1", "2": "b2"},
            "parent_of": {"r1": "b0", "b1": "r1", "b2": "b0"},
            "sites": {"b0": [500, 0], "r1": [250, 0], "b1": [0, 0], "b2": [1000, 0]}}
    plan = {"ports": [{"id": "p0", "src": {"part": "a"}, "dst": {"part": "b"}}]}
    T = CA.load(HERE.parent / "die_plan" / "clk_aocv_table_g021.json")
    arr = ({"t_a__clk": 1100.0, "t_b__clk": 1000.0}, {"b0": 100.0, "r1": 500.0, "b1": 1050.0, "b2": 950.0})
    return plan, tree, arr, T


def test_lca_and_branches(tmp_path):
    plan, tree, arr, T = _case(tmp_path)
    r = LP.analyse(plan, tree, arr, CA, T, "TT", 0.0, 416.5, "regions")[0]
    assert r["lca"] == "b0" and r["stages_a"] == 2 and r["stages_b"] == 1
    assert r["unshared_a_ps"] == 1000.0 and r["unshared_b_ps"] == 900.0 and r["d_ps"] == -100.0
    assert abs(r["dist_um"] - 1000.0) < 1e-6


def test_matches_shared_model_and_droop(tmp_path):
    plan, tree, arr, T = _case(tmp_path)
    fc = T["classes"]["A"]["TT"]["cell_share"]
    a = dict(cell_ps=fc * 1000, net_ps=(1 - fc) * 1000, stages={"A": 2})
    b = dict(cell_ps=fc * 900, net_ps=(1 - fc) * 900, stages={"A": 1})
    reg = LP.analyse(plan, tree, arr, CA, T, "TT", 0.0, 416.5, "regions")[0]
    same = LP.analyse(plan, tree, arr, CA, T, "TT", 0.0, 416.5, "same")[0]
    pdn = CA.branch_pessimism(T, "TT", a, b, 1000.0, False, "setup")
    assert abs(reg["p_dn_ps"] - round(pdn, 2)) < 0.01
    # droop charged only across regions: exactly 5.11 % of the late branch cell delay
    assert abs((reg["p_dn_ps"] - same["p_dn_ps"]) - T["droop"]["one_sided_late_frac"] * fc * 1000) < 0.02
    # d = -100 grows by p_dn (a late, b early)
    assert abs(reg["derated_abs_ps"] - (100 + reg["p_dn_ps"])) < 0.02
    assert abs(reg["margin_ps"] - (416.5 - reg["derated_abs_ps"])) < 0.02
