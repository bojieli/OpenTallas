"""QC-SLICECLK-3: --slice-spine opt-in (spine-column region trees + shared top spine, balance-aware site pass)."""
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


class FakeSite:
    """legal = inside the die and outside every blocked rect (stands in for SiteMap)."""
    def __init__(self, W, H, blocked):
        self.W, self.H, self.blocked = W, H, blocked

    def why(self, q):
        if not (0 < q[0] < self.W and 0 < q[1] < self.H):
            return "outside"
        return "core" if any(r[0] < q[0] < r[2] and r[1] < q[1] < r[3] for r in self.blocked) else None

    def legal(self, q):
        return self.why(q) is None

    def nearest(self, p, axis=None):
        best = None
        for k in range(1, 4000):
            for q in ((p[0] + k, p[1]), (p[0] - k, p[1]), (p[0], p[1] + k), (p[0], p[1] - k)):
                if self.legal(q):
                    return q
        return best


def two_slices():
    """two 400 x 3200 slices side by side; centre column of each blocked by a 'core' strip (as QC A0 halos)."""
    W, H = 800.0, 3200.0
    parts, types, R, taps = {}, {}, {}, []
    types["t"] = dict(outline_um=[400.0, 400.0])
    for s, x0 in (("A", 0.0), ("B", 400.0)):
        for j in range(8):
            n = f"{s}{j}"
            parts[n] = dict(type="t", origin_um=[x0, j * 400.0])
            R[n] = s
            for tx in (50.0, 150.0, 250.0, 350.0):
                for ty in (100.0, 300.0):
                    taps.append((n, f"clk_{tx}_{ty}", x0 + tx, j * 400.0 + ty))
    P = SimpleNamespace(W=W, H=H, clock={"spine": {"root_um": [400.0, 1600.0]}}, parts=parts, types=types)
    # cores over the slice centre column everywhere except a channel row at the band (y 1590-1610)
    blocked = [(190.0, 5.0, 210.0, 1590.0), (190.0, 1610.0, 210.0, 3195.0),
               (590.0, 5.0, 610.0, 1590.0), (590.0, 1610.0, 610.0, 3195.0)]
    return P, taps, R, FakeSite(W, H, blocked)


def test_column_levels_sit_on_the_legal_column_and_lengths_are_equal():
    P, taps, R, site = two_slices()
    nodes, info = D.build_slice_spine_tree(P, taps, R, leaf_um=200.0, site=site, top_leaf_um=20.0)
    for rn, r in info["regions"].items():
        assert r["mode"] == "spine_column"
        x = r["column_x_um"]
        assert site.legal((x, 1000.0)) and abs(x - (200.0 if rn == "A" else 600.0)) > 10
        col = [n for n in nodes.values() if n.get("spine") == "column" and n["region"][0] == (0.0 if rn == "A" else 400.0)]
        assert col and all(abs(n["x"] - x) < 1e-6 for n in col)
    # requested geometry: every root -> leaf node Manhattan length is equal (inside a slice AND across the two slices)
    L = D.path_lengths(nodes)
    leaf = {round(L[i], 3) for i, n in nodes.items() if n["taps"]}
    assert len(leaf) == 1, leaf
    # the y levels never split along x on the column; the strip leg is the same for every strip of a slice
    assert all(n.get("split") == "y" for n in nodes.values() if n.get("spine") == "column" and n.get("split"))


def test_top_spine_is_one_row():
    P, taps, R, site = two_slices()
    nodes, info = D.build_slice_spine_tree(P, taps, R, leaf_um=200.0, site=site, top_leaf_um=20.0)
    ys = {n["y"] for n in nodes.values() if n.get("spine") == "top" and n["parent"] is not None
          and not n.get("corner")}
    assert ys == {info["spine_row_y_um"]} and 1590.0 <= info["spine_row_y_um"] <= 1610.0


def test_balanced_site_prefers_the_zero_cost_move_back_along_the_incoming_leg():
    site = FakeSite(1000.0, 1000.0, [(480.0, 480.0, 520.0, 520.0)])
    p, parent = (500.0, 500.0), (500.0, 800.0)          # incoming leg vertical, kids split along x
    kids = [(400.0, 500.0), (600.0, 500.0)]
    q, cost = D.balanced_site(site, p, parent, kids, "x")
    assert cost == 0.0 and abs(q[0] - 500.0) < 1e-6 and q[1] > 520.0


def test_balanced_site_does_not_slide_along_the_split_axis_when_a_cheaper_move_exists():
    # incoming leg ALONG the split axis (the QC slice case that broke --tree-site-slide); a move across costs 2d,
    # a move along it costs 2d between siblings: the tie goes to the shorter move, never a long along-axis slide
    site = FakeSite(1000.0, 1000.0, [(300.0, 490.0, 700.0, 510.0)])
    p, parent = (500.0, 500.0), (500.0, 100.0)
    kids = [(500.0, 300.0), (500.0, 700.0)]               # split along y, incoming along y
    q, cost = D.balanced_site(site, p, parent, kids, "y")
    assert abs(q[1] - 500.0) > 5.0 or cost <= 2 * abs(q[0] - 500.0) + 1e-6
    assert cost <= 25.0, (q, cost)


def test_legal_point_is_never_moved():
    site = FakeSite(1000.0, 1000.0, [])
    assert D.balanced_site(site, (10.0, 10.0), (0.0, 0.0), [(20.0, 10.0)], "x") == ((10.0, 10.0), 0.0)


def test_find_spine_row_and_column():
    site = FakeSite(1000.0, 1000.0, [(0.0, 495.0, 1000.0, 505.0), (495.0, 0.0, 505.0, 1000.0)])
    assert site.legal((0.5 * 1000, 520.0)) is False
    y = D.find_spine_row(site, 10.0, 450.0, 500.0, step=1.0)
    assert y is not None and abs(y - 500.0) <= 6.0 and not (495 < y < 505)
    x = D.find_spine_column(site, (0.0, 0.0, 1000.0, 1000.0), step=1.0)
    assert x is None or not (495 < x < 505)


def test_default_kit_path_is_unchanged():
    sig = inspect.signature(D.clock_kit)
    assert sig.parameters["slice_spine"].default is False
    assert inspect.signature(D.write_kit).parameters["slice_spine"].default is False
    a = D.main.__code__  # CLI keeps the opt-in flag
    assert "--slice-spine" in inspect.getsource(D.main)


def test_slice_rows_reservation_overrides_column_and_spine_row():
    P, taps, R, site = two_slices()
    rows = {"lane": "R35", "schema": "qc_slice_clock_rows/1",
            "top": {"rows": {"T3_tap": {"y": 1600.0}}, "taps": [{"region": "A", "x": 250.0}, {"region": "B", "x": 650.0}]}}
    nodes, info = D.build_slice_spine_tree(P, taps, R, leaf_um=200.0, site=site, top_leaf_um=20.0, rows=rows)
    assert info["spine_row_y_um"] == 1600.0
    assert {r["column_x_um"] for r in info["regions"].values()} == {250.0, 650.0}
    L = D.path_lengths(nodes)
    assert len({round(L[i], 3) for i, n in nodes.items() if n["taps"]}) == 1


def test_round_legal_keeps_a_halo_edge_point_outside_the_halo():
    # DIE-QC 10-27: QC b3485/b5553/b8655 sat on x = 10620.72 vs halo edge 10620.720000000001 after round(q, 3)
    x0 = 10262.160000000002
    edge = x0 + 358.56
    site = FakeSite(30000.0, 30000.0, [(x0, 10832.4, edge, 11095.92)])
    q = (edge + 1e-9, 11080.8)
    if site.legal((round(q[0], 3), q[1])):       # float repr made the plain rounding legal: nothing to prove here
        q = (10620.720000000001 + 1e-12, 11080.8)
        site = FakeSite(30000.0, 30000.0, [(x0, 10832.4, 10620.720000000001, 11095.92)])
    assert site.legal(q) and not site.legal((round(q[0], 3), round(q[1], 3)))
    r = D.round_legal(site, q)
    assert site.legal(r) and abs(r[0] - q[0]) <= 1.1e-3 and r[1] == 11080.8


def test_round_legal_is_plain_rounding_when_already_legal_or_hopeless():
    site = FakeSite(100.0, 100.0, [(40.0, 40.0, 60.0, 60.0)])
    assert D.round_legal(site, (10.00049, 20.0)) == (10.0, 20.0)
    assert D.round_legal(site, (50.00049, 50.0)) == (50.0, 50.0)


def test_balanced_site_then_round_legal_never_lands_inside_a_halo():
    # the QC b3485 sequence: coarse walk from 10521.36 in 2.16 steps stops at 10620.720000000001 = the halo edge
    x0 = 10262.160000000002
    site = FakeSite(30000.0, 30000.0, [(x0, 10832.4, 10620.720000000001, 11095.92)])
    p = (10521.36, 11080.8)
    q, _ = D.balanced_site(site, p, (10521.36, 12000.0), [(10521.36, 10900.0), (10521.36, 11200.0)], "y")
    r = D.round_legal(site, q)
    assert site.legal(r) and r == (round(r[0], 3), round(r[1], 3))
