#!/usr/bin/env python3
"""QC-PLAN-R8 LINK-SITES: python3 -m pytest tools/die_plan/test_link_sites.py

Synthetic cb-like type: two hard-core tiles 850 um apart, a tile-link delay line u_d0_link (D=3) from tile A q to the
core-pin pipe register u_pc_nk that drives tile B a, and an out bus row (2 stations) from tile A t_out to the S face.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "link_sites.py"
TYPE = "qc_cb_t"

SV = """
module ot_bound_qc_cb_t (input logic clk);
  logic [7:0] a_q, t_q, d0_q, pc_q, bo_q;
  ot_tile_a u_ta (.clk(clk), .q(a_q), .t_out(t_q));
  ot_dp_dly #(.W(8), .D(3)) u_d0_link (.clk(clk), .d(a_q), .q(d0_q));
  ot_dp_dly #(.W(8), .D(1)) u_pc_nk (.clk(clk), .d(d0_q), .q(pc_q));
  ot_tile_b u_tb (.clk(clk), .a(pc_q));
  ot_dp_st #(.W(8)) u_bout_bx (.clk(clk), .d(t_q), .q(bo_q));
endmodule
"""


def _pins(port, x, y0):
    return [dict(name=f"{port}[{i}]", x=x, y=y0 + i) for i in range(8)]


def _fixture(tmp, budgets=None):
    root = tmp / "pins"
    root.mkdir()
    # tile A (100 x 200 at 50,100): q on its east edge, t_out on its north edge
    (root / "tile_a.pins.json").write_text(json.dumps(dict(
        pins=_pins("q", 100.0, 96.0) + [dict(name=f"t_out[{i}]", x=60.0 + i, y=200.0) for i in range(8)])))
    # tile B (100 x 200 at 1000,100): a on its west edge
    (root / "tile_b.pins.json").write_text(json.dumps(dict(pins=_pins("a", 0.0, 96.0))))
    t = dict(
        outline_um=[1200.0, 400.0],
        hard_cores=[
            dict(inst="u_ta", origin_um=[50.0, 100.0], outline_um=[100.0, 200.0], orient="R0", pins_file="tile_a.pins.json"),
            dict(inst="u_tb", origin_um=[1000.0, 100.0], outline_um=[100.0, 200.0], orient="R0", pins_file="tile_b.pins.json"),
        ],
        buses=[dict(name="bx", face="S", window_um=[550.0, 650.0], dir="out")],
        internal_stations=[dict(conn="bus:bx", regs_um=[[300.0, 250.0], [450.0, 100.0]], from_um=[120.0, 320.0],
                                to_um=[600.0, 0.0], bits=8)],
        relay_sites={},
    )
    raw = dict(partition_types={TYPE: t})
    if budgets is not None:
        raw["budgets"] = budgets
    plan = tmp / "plan.json"
    plan.write_text(json.dumps(raw))
    sv = tmp / "bound.sv"
    sv.write_text(SV)
    return plan, sv, root


def _run(tmp, plan, sv, root, tag, *extra):
    out, rep = tmp / f"out_{tag}.json", tmp / f"rep_{tag}.json"
    r = subprocess.run([sys.executable, "-I", str(TOOL), str(plan), TYPE, str(sv), str(out), str(rep), "--pins-root", str(root),
                        "--cap", "300", "--target", "299", *extra], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(out.read_text()), json.loads(rep.read_text()), out.read_bytes(), rep.read_bytes()


def test_deterministic(tmp_path):
    plan, sv, root = _fixture(tmp_path)
    a = _run(tmp_path, plan, sv, root, "a")
    b = _run(tmp_path, plan, sv, root, "b")
    assert a[2] == b[2] and a[3] == b[3]


def test_feasible_legs_within_cap(tmp_path):
    plan, sv, root = _fixture(tmp_path)
    out, rep, _o, _r = _run(tmp_path, plan, sv, root, "f")
    assert rep["legs"] > 0 and rep["legs_over_cap"] == 0
    assert rep["worst_leg_um"] <= 300.0
    assert all(d <= 300.0 for d, _a, _b in rep["all_legs"])
    # the link chain is placed: tile A pin -> 3 delay stages -> pipe register at tile B pin -> tile B pin
    sites = out["partition_types"][TYPE]["relay_sites"]
    for s in ("u_d0_link.r[0]", "u_d0_link.r[1]", "u_d0_link.q", "u_pc_nk.q"):
        assert all(f"{s}[{b}]" in sites for b in range(8)), s
    # u_pc_nk sits at its core pin (just west of tile B)
    assert all(990.0 <= sites[f"u_pc_nk.q[{b}]"][0] < 1000.0 for b in range(8))


def test_min_stations_grows_row(tmp_path):
    plan, sv, root = _fixture(tmp_path)
    base, rep0, _o, _r = _run(tmp_path, plan, sv, root, "m0")
    n0 = len(base["partition_types"][TYPE]["internal_stations"][0]["regs_um"])
    grown, rep1, _o, _r = _run(tmp_path, plan, sv, root, "m1", "--min-stations", f"bx={n0 + 2}")
    n1 = len(grown["partition_types"][TYPE]["internal_stations"][0]["regs_um"])
    assert n1 >= n0 + 2
    assert rep1["cycles"]["bx"] == dict(before=2, after=n1, dir="out")
    assert rep1["legs_over_cap"] == 0


def test_seg0_leaves_lockup_budget(tmp_path):
    budgets = dict(r_dly_lockup=dict(other_type=dict(seg=4)))
    plan, sv, root = _fixture(tmp_path, budgets)
    out, rep, _o, _r = _run(tmp_path, plan, sv, root, "s0", "--seg", "0")
    assert out["budgets"] == budgets
    assert rep["seg"] == 0
    assert "u_d0_link.q[0]" in out["partition_types"][TYPE]["relay_sites"]


def test_seg1_writes_lockup_budget(tmp_path):
    plan, sv, root = _fixture(tmp_path)
    out, rep, _o, _r = _run(tmp_path, plan, sv, root, "s1", "--seg", "1")
    assert out["budgets"]["r_dly_lockup"][TYPE] == dict(seg=1)
    assert rep["seg"] == 1
    sites = out["partition_types"][TYPE]["relay_sites"]
    # stage names follow the segment split (kit_dly_lockup <inst>_sg<j>)
    assert all(f"u_d0_link_sg{j}.q[0]" in sites for j in range(3))
    assert not any(k.startswith("u_d0_link.") for k in sites)


def _pc_legs(rep):
    return [d for d, a, b in rep["all_legs"] if "u_pc_nk" in a and "u_tb" in b or "u_pc_nk" in b and "u_tb" in a]


def test_pc_slack0_identical(tmp_path):
    plan, sv, root = _fixture(tmp_path)
    a = _run(tmp_path, plan, sv, root, "p_def")
    b = _run(tmp_path, plan, sv, root, "p_0", "--pc-slack", "0")
    assert a[2] == b[2] and a[3] == b[3]
    sites = a[0]["partition_types"][TYPE]["relay_sites"]
    assert all(990.0 <= sites[f"u_pc_nk.q[{i}]"][0] < 1000.0 for i in range(8))
    assert _pc_legs(a[1]) and all(d == 8.0 for d in _pc_legs(a[1]))


def test_pc_slack_shortens_long_link(tmp_path):
    plan, sv, root = _fixture(tmp_path)
    sv.write_text(SV.replace(".D(3)) u_d0_link", ".D(1)) u_d0_link"))   # 1 stage: ~845 um cannot meet the cap with pc AT the pin
    _o0, rep0, _a, _b = _run(tmp_path, plan, sv, root, "l0")
    assert rep0["worst_leg_um"] > 300.0
    S = 300.0
    out, rep, _a, _b = _run(tmp_path, plan, sv, root, "l1", "--pc-slack", str(S))
    assert rep["worst_leg_um"] < rep0["worst_leg_um"]
    sites = out["partition_types"][TYPE]["relay_sites"]
    for i in range(8):
        x, y = sites[f"u_pc_nk.q[{i}]"]
        assert abs(x - 1000.0) + abs(y - (196.0 + i)) <= S + 15.0, (i, x, y)
    legs = _pc_legs(rep)
    assert legs and max(legs) > 8.0
    assert all(d <= S + 1.0 for d in legs)
