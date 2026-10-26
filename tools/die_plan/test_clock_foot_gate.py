"""clock_foot_gate unit tests (plan-free): foot on an island crossed by a strap, footless when no strap crosses a site."""
import clock_foot_gate as G


def test_foot_on_island_under_strap():
    xs, ys = [100.0, 500.0], [100.0]
    segs = G.strap_segments(xs, ys, [dict(rect_um=[496.0, 296.0, 504.0, 304.0], owner="c0")])
    b = G.foot(xs, ys, segs, 500.0, 300.0, 405.0)
    assert b is not None and b[0] == 0.0 and b[3] == "c0" and b[2] == "M9[1]"


def test_footless_island_off_lattice():
    xs, ys = [100.0, 500.0], [100.0]
    segs = G.strap_segments(xs, ys, [dict(rect_um=[296.0, 296.0, 304.0, 304.0], owner="c1")])
    assert G.foot(xs, ys, segs, 300.0, 300.0, 405.0) is None


def test_reach_limit():
    xs, ys = [0.0], [0.0]
    segs = G.strap_segments(xs, ys, [dict(rect_um=[-4.0, 500.0, 4.0, 508.0], owner="far")])
    assert G.foot(xs, ys, segs, 0.0, 0.0, 405.0) is None
    assert G.foot(xs, ys, segs, 0.0, 0.0, 600.0)[0] == 500.0


def test_soft_site_callback():
    xs, ys = [0.0], [0.0]
    b = G.foot(xs, ys, {}, 10.0, 50.0, 405.0, soft=lambda ax, s, along, room: along)
    assert b is not None and b[3] == "soft" and b[0] == 10.0
