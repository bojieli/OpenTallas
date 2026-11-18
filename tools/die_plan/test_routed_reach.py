"""ROUTED-REACH (KV-PV-RIDER 11-18, routed_reach.py): exact routed length round blocking cores, the LEF-OBS blocking
rule, and the G0 hook (warn default, error opt-in, off).
    python3 -m pytest -q tools/die_plan/test_routed_reach.py"""
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import routed_reach as RR  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _lef(path, obs_layers, pin_layer="M5", w=200.0, h=100.0):
    obs = "".join(f"    LAYER {L} ;\n     RECT  0 0 {w} {h} ;\n" for L in obs_layers)
    path.write_text(f"MACRO c\n  SIZE {w} BY {h} ;\n  PIN a\n    PORT\n      LAYER {pin_layer} ;\n       RECT 0 0 1 1 ;\n"
                    f"    END\n  END a\n  OBS\n{obs}  END\nEND c\n")
    return str(path)


def test_route_straight_when_clear():
    L, poly = RR.route((0, 0), (100, 50), [], (500, 500))
    assert L == 150 and poly[0] == (0.0, 0.0) and poly[-1] == (100.0, 50.0)


def test_route_round_a_box():
    box = (100.0, 0.0, 300.0, 200.0, "c")
    # both L-paths cross the box: the route goes over its top edge
    L, poly = RR.route((50.0, 100.0), (350.0, 100.0), [box], (1000.0, 1000.0))
    assert math.isclose(L, 300.0 + 2 * 100.0)
    assert all(not RR._strict_in(p, box) for p in poly)
    # one L-path is free: Manhattan
    L2, _ = RR.route((50.0, 250.0), (350.0, 100.0), [box], (1000.0, 1000.0))
    assert math.isclose(L2, 300.0 + 150.0)


def test_route_outline_bounds_the_detour():
    box = (100.0, 0.0, 300.0, 200.0, "c")
    # the box touches y = 0: no slot between it and the outline, the route goes over the top
    L, _ = RR.route((50.0, 20.0), (350.0, 20.0), [box], (1000.0, 1000.0))
    assert math.isclose(L, 300.0 + 2 * 180.0)
    L2, _ = RR.route((50.0, 20.0), (350.0, 20.0), [box], None)       # no outline: under the box along y = 0 is open
    assert math.isclose(L2, 300.0 + 2 * 20.0)


def test_route_abutting_boxes_have_no_slot():
    a, b = (100.0, 0.0, 300.0, 100.0, "a"), (100.0, 100.0, 300.0, 200.0, "b")
    L, poly = RR.route((50.0, 100.0), (350.0, 100.0), [a, b], (1000.0, 1000.0))
    assert math.isclose(L, 300.0 + 2 * 100.0)        # over the top of b, never along the shared edge y = 100


def test_route_endpoint_inside_escapes():
    box = (100.0, 0.0, 300.0, 200.0, "c")
    L, _ = RR.route((110.0, 100.0), (350.0, 100.0), [box], (1000.0, 1000.0))
    assert math.isclose(L, 190.0 + 50.0)              # out of the nearest useful side (E), then straight
    L2, _ = RR.route((110.0, 100.0), (50.0, 100.0), [box], (1000.0, 1000.0))
    assert math.isclose(L2, 10.0 + 50.0)


def test_points_on_and_hops():
    poly = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]
    assert RR.points_on(poly, [0.5]) == [(100.0, 0.0)]
    hs = RR.hops([(0, 0), (100, 0)], [], None)
    assert hs == [(0, 100, 100)]


def test_obs_top_and_blocking_rule(tmp_path):
    hi = _lef(tmp_path / "hi.lef", ["M1", "M2", "M3", "M4", "M5", "M6", "M7"])
    lo = _lef(tmp_path / "lo.lef", ["M1", "M2", "M3", "M4", "M5"], pin_layer="M7")   # an M7 PIN is not an OBS
    assert RR.obs_top(hi) == 7 and RR.obs_top(lo) == 5 and RR.obs_top(str(tmp_path / "none.lef")) is None
    t = dict(outline_um=[1000.0, 1000.0], hard_cores=[
        dict(inst="h", origin_um=[100.0, 0.0], outline_um=[200.0, 100.0], track_offset_um=[1.0, 0.0], lef=hi),
        dict(inst="l", origin_um=[500.0, 0.0], outline_um=[200.0, 100.0], lef=lo),
        dict(inst="d", origin_um=[0.0, 500.0], outline_um=[100.0, 100.0], obs_max="M7"),
        dict(inst="n", origin_um=[500.0, 500.0], outline_um=[100.0, 100.0], orient="R90")])
    boxes, info = RR.blocking_boxes(t, "M7")
    assert [b[4] for b in boxes] == ["h", "d"] and info["n"] == "no_view"
    assert boxes[0][:4] == (101.0, 0.0, 301.0, 100.0)


def _plan(tmp_path, regs):
    p = copy.deepcopy(EX)
    t = p["partition_types"]["mid"]
    t["hard_cores"] = [dict(inst="blk", module="blk", origin_um=[300.0, 0.0], outline_um=[200.0, 300.0],
                            track_offset_um=[0.0, 0.0], lef=_lef(tmp_path / "blk.lef", ["M%d" % k for k in range(1, 8)],
                                                                 w=200.0, h=300.0))]
    t["internal_stations"] = [dict(conn="bus:x", from_um=[250.0, 100.0], to_um=[700.0, 300.0], regs_um=regs,
                                   launch="a", capture="b", note="test")]
    return p


def test_plan_report_and_g0_hook(tmp_path):
    import check as CK
    bad = _plan(tmp_path, [[550.0, 100.0]])              # 300 um Manhattan, routed 700 round blk (it abuts y = 0)
    rep = RR.plan_report(bad)
    assert len(rep["over"]) == 1 and rep["over"][0]["hop"] == 0 and math.isclose(rep["over"][0]["routed"], 700.0)
    assert math.isclose(rep["over"][0]["man"], 300.0)
    R, s = CK.run(copy.deepcopy(bad))
    assert s["routed_reach"]["mode"] == "warn" and s["routed_reach"]["over"] == 1
    assert not [e for e in R.errors() if e["check"] == "routed_reach"]
    assert [w for w in R.items if w["check"] == "routed_reach"]
    Re, se = CK.run(copy.deepcopy(bad), routed_reach="error")
    assert [e for e in Re.errors() if e["check"] == "routed_reach"] and se["routed_reach"]["mode"] == "error"
    bb = copy.deepcopy(bad)
    bb["budgets"]["routed_reach"] = "error"
    Rb, _ = CK.run(bb)
    assert [e for e in Rb.errors() if e["check"] == "routed_reach"]
    Ro, so = CK.run(copy.deepcopy(bad), routed_reach="off")
    assert so["routed_reach"] == dict(mode="off")
    good = _plan(tmp_path, [[290.0, 310.0], [510.0, 310.0]])   # stations in the channels beside blk: every hop <= 405
    rg = RR.plan_report(good)
    assert rg["over"] == [] and rg["max_routed_um"] <= 405.0
    Rg, sg = CK.run(copy.deepcopy(good), routed_reach="error")
    assert not [e for e in Rg.errors() if e["check"] == "routed_reach"] and sg["routed_reach"]["over"] == 0


def test_cli(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps(_plan(tmp_path, [[550.0, 100.0]])))
    assert RR.main(["check", str(f), "--json", str(tmp_path / "r.json")]) == 1
    assert json.loads((tmp_path / "r.json").read_text())["schema"] == RR.SCHEMA
    f.write_text(json.dumps(_plan(tmp_path, [[290.0, 310.0], [510.0, 310.0]])))
    assert RR.main(["check", str(f)]) == 0
