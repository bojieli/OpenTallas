import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fwdclk_repoint as FR  # noqa: E402

NAN = float("nan")


def c(k, hop, mn, mx, tap="t", xy=(0, 0), pin=(0, 0)):
    return dict(k=k, hop=hop, min=mn, max=mx, tap=tap, xy=list(xy), pin=list(pin))


def test_choose_nearest_qualifying():
    got, ok = FR.choose([c(0, 10, 30, 99), c(1, 60, 20, 80)], 150)
    assert ok and got["k"] == 0


def test_choose_skips_setup_loss_and_keeps_bound():
    # nearest makes max 255 > max(206, 166.6) + 5: the 2nd tap (185) qualifies under before 206
    got, ok = FR.choose([c(0, 27, 148, 255), c(1, 49, 24, 185)], 206)
    assert ok and got["k"] == 1


def test_choose_none_ok_is_least_bad():
    got, ok = FR.choose([c(0, 22, 300, 384), c(1, 80, 290, 300)], 265)
    assert ok is False and got["k"] == 1


def test_choose_hold_contract():
    got, ok = FR.choose([c(0, 10, -400, 50), c(1, 50, -100, 60)], 100)
    assert ok and got["k"] == 1


def test_map_tap_pin_offset_and_limit():
    grid = {"clk": (0, 0), "a": (100, 0), "b": (500, 0)}
    n, err = FR.map_tap(grid, (110, 0), c(0, 5, 0, 0, xy=(95, 0), pin=(100, 0)))
    assert n == "a" and err == 5.0


def _type(src):
    return {"clock": {"landing_contract": {"pins": [
        {"name": "fclk_out_x", "kind": "clock", "dir": "out", "source_clock_port": src, "source_clock_tap": src,
         "xy_um": [0, 0]}]}}}


def test_repoint_unmeasured_is_nearest_and_writes_tap():
    grid = {"clk": (0, 0), "far": (400, 0), "near": (20, 0)}
    t = _type("far")
    rows = FR.repoint_type("T", t, grid)
    q = t["clock"]["landing_contract"]["pins"][0]
    assert rows[0]["basis"] == "UNMEASURED" and q["source_clock_port"] == "near" and q["source_clock_tap"] == "near"


def test_repoint_measured_picks_whatif_tap():
    grid = {"clk": (0, 0), "far": (400, 0), "near": (20, 0), "mid": (60, 0)}
    t = _type("far")
    w = {"fclk_out_x": {"min_b": 100, "max_b": 200, "cand": {
        "0": dict(tap="k0", hop=20, xy=[20, 0], pin=[0, 0], min=150, max=260),
        "1": dict(tap="k1", hop=60, xy=[60, 0], pin=[0, 0], min=40, max=180)}}}
    rows = FR.repoint_type("T", t, grid, w)
    assert rows[0]["new"] == "mid" and rows[0]["basis"] == "measured"


def test_repoint_leaves_near_sources_and_unfixable():
    grid = {"clk": (0, 0), "ok": (100, 0)}
    t = _type("ok")
    assert FR.repoint_type("T", t, grid) == []
    grid2 = {"clk": (0, 0), "a": (400, 0), "b": (350, 0)}
    assert FR.repoint_type("T", _type("a"), grid2) == []      # no tap within the limit: not repointable here


def test_follow_shifts_by_core_delta():
    def ty(org, txy):
        return {"clock": {"core_taps": "early", "taps": [{"kind": "core", "name": "u_k.clk", "xy": list(txy)}]},
                "hard_cores": [{"inst": "u_k", "origin_um": list(org), "outline_um": [10, 10]}]}
    b = ty((0, 300), (5, 305))
    t = ty((0, 104), (5, 305))
    rows = FR.follow_type("T", t, b)
    assert rows and t["clock"]["taps"][0]["xy"] == [5.0, 109.0]
    assert FR.follow_type("T", t, b) == []
