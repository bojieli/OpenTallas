"""S81-BANDTAP-1115: ring bands honour clock.tap_reserved_um / clock.band_keepout_um (single-rect _storage_band and
multi-rect _storage_rects) and the multi-rect carve never uses more pieces than the plain greedy."""
import pytest

import clock_landing_plan as CL

# 400 x 400 type, bus pin at (200, 0) on the S face; free rows only y 17.28-60 (a 42.7-um channel across the die)
OBST = [[0, 60, 400, 400], [0, 0, 17.28, 60], [383, 0, 400, 60]]


def _type(taps=(), keepout=()):
    t = {"outline_um": [400, 400],
         "buses": [{"name": "b", "dir": "in", "face": "S", "window_um": [190, 210], "width": 100}],
         "clock": {"landing_contract": {"bands": {"b": {"placement": "FAIL", "rect_um": None, "instance": "u_cland_b"}}}}}
    if taps:
        t["clock"]["tap_reserved_um"] = [list(r) for r in taps]
    if keepout:
        t["clock"]["band_keepout_um"] = [list(r) for r in keepout]
    return t


@pytest.fixture(autouse=True)
def blocked(monkeypatch):
    monkeypatch.setattr(CL.RT, "blockages", lambda t, *a, **k: [list(o) for o in OBST])


def _hits(rects, sites):
    return [r for r in rects if any(CL._rect_overlap(r, o) for o in sites)]


def test_single_band_default_ignores_nothing_when_no_taps():
    b = CL._storage_band(_type(), "b", 100, [])
    assert b["rect_um"]


def test_single_band_slides_off_tap_site():
    base = CL._storage_band(_type(), "b", 100, [])["rect_um"]
    site = [(base[0] + base[2]) / 2 - 4.32, (base[1] + base[3]) / 2 - 4.32, (base[0] + base[2]) / 2 + 4.32, (base[1] + base[3]) / 2 + 4.32]
    b = CL._storage_band(_type(taps=[site]), "b", 100, [])
    assert b["rect_um"] != base and not _hits([b["rect_um"]], [site])
    assert b["max_pin_to_band_hop_um"] <= 405 - 2.16


def test_single_band_honours_band_keepout():
    base = CL._storage_band(_type(), "b", 100, [])["rect_um"]
    win = [base[0], base[1], base[0] + 8.64, base[1] + 8.64]
    b = CL._storage_band(_type(keepout=[win]), "b", 100, [])
    assert not _hits([b["rect_um"]], [win])


def test_multi_rect_obstacles_include_taps_and_keepouts():
    t = _type(taps=[[100, 20, 108.64, 28.64]], keepout=[[200, 20, 208.64, 28.64]])
    ob = CL._band_obstacles(t, [])
    assert [100, 20, 108.64, 28.64] in ob and [200, 20, 208.64, 28.64] in ob


def test_multi_rect_defrag_never_more_pieces_and_clear_of_taps():
    taps = [[x, 20 + 9.72 * (k % 3), x + 8.64, 28.64 + 9.72 * (k % 3)] for k, x in enumerate(range(40, 360, 38))]
    t = _type(taps=taps)
    greedy = CL._storage_rects_one(t, "b", 100, [])
    best = CL._storage_rects(t, "b", 100, [])
    n = lambda b: len(b.get("rects_um") or [b["rect_um"]])
    assert n(best) <= n(greedy)
    rs = best.get("rects_um") or [best["rect_um"]]
    assert not _hits(rs, taps)
    assert all(CL._hop(r, 200, 0) <= 405 - 2.16 for r in rs)
    assert sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) + 1e-6 >= best["area_reserve_um2"]


def test_tap_reach_keeps_band_points_near_a_tap_site():
    t = _type()
    t["clock"]["taps"] = [{"name": "clk_t1", "xy": [300.0, 30.0]}]
    t["clock"]["band_tap_reach_um"] = 100.0
    free = CL._storage_rects(_type(), "b", 100, [])                 # without the row the band sits by the pin (x ~200)
    b = CL._storage_rects(t, "b", 100, [])
    rs = b.get("rects_um") or [b["rect_um"]]
    for r in rs:
        for x in (r[0], r[2]):
            for y in (r[1], r[3]):
                assert abs(x - 300.0) + abs(y - 30.0) <= 100.0 + 1.08
    assert (free.get("rects_um") or [free["rect_um"]]) != rs


def test_tap_reach_off_is_unchanged():
    a = CL._storage_rects(_type(), "b", 100, [])
    t = _type(); t["clock"]["taps"] = [{"name": "clk_t1", "xy": [300.0, 30.0]}]
    assert CL._storage_rects(t, "b", 100, []) == a


def test_tap_reach_no_site_in_reach_raises():
    t = _type()
    t["clock"]["taps"] = [{"name": "clk_t1", "xy": [30.0, 300.0]}]
    t["clock"]["band_tap_reach_um"] = 50.0
    with pytest.raises(ValueError):
        CL._storage_rects(t, "b", 100, [])
