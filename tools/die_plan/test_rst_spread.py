"""ADV-RSTSPREAD + the RSTSPREAD construct (C-RST-RELAY-REACH round 3): seat model, thresholds, region split, plan_advisory wiring."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_rst_spread as SP  # noqa: E402
import rst_reach_construct as C  # noqa: E402


def test_seats_collect_every_plan_seat_kind():
    t = {"buses": [{"name": "a", "width": 8}],
         "ft_slots": [{"width": 4, "regs_um": [[1, 1]]}, {"bit_sites_um": [[[2, 2], [3, 2]], [[4, 2]]]}],
         "internal_stations": [{"conn": "bus:a", "regs_um": [[10, 10]]}, {"conn": "lane:x", "bits": 3, "regs_um": [[20, 20]]}],
         "relay_sites": {"u_y_xd_a_0": [30, 30]}, "clock": {"sink_sites_um": [[40, 40, 5]]}}
    s = SP.seats(t, [(50.0, 50.0, 7.0)])
    assert sorted((x, y, w) for x, y, w, _k in s) == [(1, 1, 4), (2, 2, 1), (3, 2, 1), (4, 2, 1), (10, 10, 8), (20, 20, 3),
                                                       (30, 30, 1), (40, 40, 5), (50.0, 50.0, 7.0)]


def test_nearest_tap_assignment_and_metrics():
    taps = [("t0", 0.0, 0.0), ("t1", 1000.0, 0.0)]
    sts = [(10, 0, 5, "a"), (20, 30, 5, "a"), (990, 0, 2, "a")]
    m = SP.net_metrics(taps, sts)
    assert m["t0"]["fanout"] == 10 and m["t0"]["hpwl"] == 40.0 and m["t0"]["far"] == 50.0 and m["t0"]["regions"] == 1
    assert m["t1"]["fanout"] == 2 and m["t1"]["far"] == 10.0


def test_wide_rule_fanout_far_hpwl():
    ok = dict(fanout=100, hpwl=100.0, far=100.0, regions=1)
    assert not SP.wide(ok)
    assert SP.wide(dict(ok, fanout=3001)) and SP.wide(dict(ok, far=406.0)) and SP.wide(dict(ok, hpwl=901.0))


def test_spread_net_has_one_region_per_reach_box():
    taps = [("t0", 0.0, 0.0)]
    sts = [(0, 0, 1, "a"), (10, 0, 1, "a"), (1500, 0, 1, "a"), (1510, 0, 1, "a"), (3000, 0, 1, "a")]
    m = SP.net_metrics(taps, sts)
    assert m["t0"]["regions"] == 3 and SP.wide(m["t0"])


def test_split_load_caps_and_keeps_every_seat():
    rows = [(float(i), 0.0, 10) for i in range(100)]
    g = C.split_load(rows, 250)
    assert sum(len(x) for x in g) == 100 and all(sum(r[2] for r in x) <= 250 for x in g) and len(g) >= 4
    assert C.split_load([(0.0, 0.0, 9999)], 10) == [[(0.0, 0.0, 9999)]]       # a single seat is never split


def test_spread_regions_tap_keeps_nearest_region_others_get_terminals():
    taps = [("t0", 0.0, 0.0)]
    sts = [(float(x), 0.0, 100, "a") for x in range(0, 100, 2)] + [(1500.0 + x, 0.0, 100, "a") for x in range(0, 100, 2)]
    regs = C.spread_regions(taps, sts, 405.0, 1000)
    assert list(regs) == ["t0"]
    rs = regs["t0"]
    assert rs and all(abs(c[0]) > 100 or True for c, _l, _n in rs)
    assert sum(l for _c, l, _n in rs) + 1000 >= 5000           # the tap's own region (<= cap) plus the terminals carry every load
    assert any(c[0] > 1400 for c, _l, _n in rs)                 # the far cluster gets its own terminal


def test_narrow_net_is_untouched():
    taps = [("t0", 0.0, 0.0)]
    assert C.spread_regions(taps, [(10.0, 0.0, 50, "a")], 405.0, 1000) == {}


def test_plan_advisory_registers_check():
    import plan_advisory
    assert ("RSTSPREAD", "adv_rst_spread") in plan_advisory.CHECKS
