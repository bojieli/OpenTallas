"""C-TAP-REACH (QC-INT-R2-TOOLS 11-26): tap_reach seats / census / PRE lines, with the cA4 coll_ft east relay column as the fixture."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tap_reach as TR  # noqa: E402

CA4_TAPS = {"clk": (365.024, 17.312), "clk_t2": (119.968, 279.328), "clk_t3": (365.024, 279.328), "clk_t5": (365.024, 610.528),
            "clk_t8": (777.12, 776.16), "clk_t10": (387.36, 471.84), "clk_t13": (262.048, 705.824), "clk_t18": (464.454, 8.775)}


def _type(**kw):
    t = {"outline_um": [786.24, 941.76],
         "clock": {"tap_mode": "explicit", "tap_radius_um": 200.0,
                   "landing_contract": {"collector_tree": {"relays": [
                       {"name": "u_rrl_37", "xy": [655.2, 453.824]}, {"name": "u_rrl_38", "xy": [655.2, 231.216]},
                       {"name": "u_rrl_39", "xy": [655.2, 8.608]}, {"name": "u_rrl_34", "xy": [655.2, 676.432]}]}}}}
    t.update(kw)
    return t


def _raw(t):
    return {"die": {"name": "qwen_compute"}, "partition_types": {"coll_ft__cla4a25d77": t}}


def test_east_relay_column_flagged():
    t = _type()
    res = TR.census(_raw(t), {"coll_ft__cla4a25d77": (CA4_TAPS, set(), None)})
    r = res["coll_ft__cla4a25d77"]
    assert r["over"] == 3 and r["far"] == 1 and r["worst"] == 338.3     # y 231 (338.3), y 454 (285.9), y 676 (221.6) beyond 200; y 8 reaches
    assert [o[2] for o in r["offenders"]] == ["u_rrl_38", "u_rrl_37", "u_rrl_34"]
    lines = TR.findings(_raw(t), res)
    assert lines[0].startswith("WARN TAPREACH coll_ft__cla4a25d77: 3 of 4 FIRM seat(s)") and "worst 338.3 um" in lines[0]
    assert lines[-1].startswith("LIST TAPREACH die qwen_compute") and "flagged 1" in lines[-1] and "worst 338.3" in lines[-1]


def test_block_env_makes_fail(monkeypatch):
    monkeypatch.setenv("OT_PRE_TAPREACH_BLOCK", "1")
    t = _type()
    lines = TR.findings(_raw(t), TR.census(_raw(t), {"coll_ft__cla4a25d77": (CA4_TAPS, set(), None)}))
    assert lines[0].startswith("FAIL TAPREACH ")


def test_added_sink_tap_clears_the_column():
    taps = dict(CA4_TAPS, clk_t20=(655.2, 231.2), clk_t21=(655.2, 453.8), clk_t22=(655.2, 676.4))
    t = _type()
    assert TR.census(_raw(t), {"coll_ft__cla4a25d77": (taps, set(), None)})["coll_ft__cla4a25d77"]["over"] == 0
    assert TR.findings(_raw(t), TR.census(_raw(t), {"coll_ft__cla4a25d77": (taps, set(), None)}))[0].startswith("LIST TAPREACH")


def test_manhattan_and_radius_from_plan():
    t = _type()
    t["clock"]["tap_radius_um"] = 340.0
    res = TR.census(_raw(t), {"coll_ft__cla4a25d77": (CA4_TAPS, set(), None)})
    assert res["coll_ft__cla4a25d77"]["over"] == 0


def test_core_taps_are_not_flop_taps():
    taps = dict(CA4_TAPS, clk_c0=(655.2, 231.2))
    t = _type()
    r = TR.census(_raw(t), {"coll_ft__cla4a25d77": (taps, {"clk_c0"}, None)})["coll_ft__cla4a25d77"]
    assert r["over"] == 3


def test_unsolved_grid_falls_back_to_explicit_rows_else_unchecked():
    t = _type()
    t["clock"]["taps"] = [{"name": n, "xy": list(v)} for n, v in CA4_TAPS.items()]
    assert TR.census(_raw(t), {"coll_ft__cla4a25d77": ({}, set(), "boom")})["coll_ft__cla4a25d77"]["over"] == 3
    t2 = _type()
    t2["clock"]["tap_mode"] = "density"
    r = TR.census(_raw(t2), {"coll_ft__cla4a25d77": ({}, set(), "boom")})
    assert "unchecked" in r["coll_ft__cla4a25d77"]
    assert TR.findings(_raw(t2), r)[0].startswith("WARN TAPREACH-UNCHECKED")


def test_seat_categories():
    t = _type(relay_sites={"u_bin_a/q": [1.0, 2.0]}, internal_stations=[{"conn": "bus:x", "regs_um": [[3, 4], [5, 6]]}],
              ft_slots=[{"name": "s", "regs_um": [[7, 8]]}])
    t["clock"]["sink_sites_um"] = [[9, 10, 2.0]]
    t["clock"]["landing_local_resets"] = [{"name": "start_0", "xy_um": [11, 12]}]
    cats = sorted({s[0] for s in TR.seats(t)})
    assert cats == ["clock sink site", "collector relay", "landing reset", "relay site", "station reg"]
    assert len(TR.seats(t)) == 4 + 1 + 2 + 1 + 1 + 1


def test_nearest_python_matches_numpy(monkeypatch):
    pts = [(0.0, 0.0), (100.0, 50.0), (400.0, 400.0)]
    taps = [("a", 10.0, 10.0), ("b", 390.0, 390.0)]
    d1, i1 = TR.nearest(pts, taps)
    monkeypatch.setitem(sys.modules, "numpy", None)
    d2, i2 = TR.nearest(pts, taps)
    assert (d1, i1) == (d2, i2) == ([20.0, 130.0, 20.0], [0, 0, 1])


def test_assigned_tap_overrides_nearest():
    """HEAD ctl_n: fixed_taps pins u_rrl_15 to a tap 526 um away; the nearest tap is 40 um away -> must be flagged by assigned tap"""
    taps = {"clk_t3": (100.0, 100.0), "clk_t13": (900.0, 400.0)}
    t = {"outline_um": [1000.0, 500.0],
         "clock": {"tap_mode": "explicit", "tap_radius_um": 250.0, "tap_group": {"re": "x", "fixed_taps": {"u_rrl_15": "clk_t13"}}},
         "relay_sites": {"u_rrl_15/q": [140.0, 100.0], "u_rrl_16/q": [140.0, 100.0]}}
    res = TR.census(_raw(t), {"coll_ft__cla4a25d77": (taps, set(), None)})
    r = res["coll_ft__cla4a25d77"]
    assert r["over"] == 1 and [o[2] for o in r["offenders"]] == ["u_rrl_15/q"] and r["offenders"][0][5] == "clk_t13"
