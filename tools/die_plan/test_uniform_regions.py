"""CLOCK-KV-R2 --uniform-regions: strap boxes on the uniform lattice, LCA CPPR node, gate."""
import pytest

import die_clock_mesh as DM


def _lat(n, span):
    return [(i + .5) * span / n for i in range(n)]


def test_boxes_follow_cuts_not_tree_split():
    xs, ys = _lat(8, 800.0), _lat(8, 800.0)
    R = DM.uniform_region_boxes(xs, ys, 800.0, 800.0, dict(x_cuts_um=[500.0], y_cuts_um=[]))
    assert [(g["i0"], g["i1"], g["j0"], g["j1"]) for g in R] == [(0, 5, 0, 8), (5, 8, 0, 8)]
    # west box crosses the x bisection at i=4 -> only the die root is common; east box sits in the right half
    assert R[0]["tag"] == "h" and R[1]["tag"].startswith("h1") and R[0]["box_um"] == [0.0, 0.0, 500.0, 800.0]
    for g in R:   # LCA = common prefix of every intersection's tag
        tags = [DM.htree_tag(i, j, 8, 8) for i in range(g["i0"], g["i1"]) for j in range(g["j0"], g["j1"])]
        assert all(t.startswith(g["tag"]) for t in tags)
        assert len({t[len(g["tag"])] for t in tags}) == 2 or len(g["tag"]) == len(tags[0])


def test_aligned_cut_gives_subtree_root():
    xs, ys = _lat(8, 800.0), _lat(8, 800.0)
    R = DM.uniform_region_boxes(xs, ys, 800.0, 800.0, dict(x_cuts_um=[400.0]))
    assert [g["tag"] for g in R] == ["h0", "h1"]


def test_bad_cuts():
    xs, ys = _lat(4, 400.0), _lat(4, 400.0)
    with pytest.raises(ValueError):
        DM.uniform_region_boxes(xs, ys, 400.0, 400.0, dict(x_cuts_um=[10.0]))      # empty interval
    with pytest.raises(ValueError):
        DM.uniform_region_boxes(xs, ys, 400.0, 400.0, dict(x_cuts_um=[300.0, 200.0]))


def test_lattice_spec_validation():
    """CLOCK-KV-R3 --lattice-spec: power-of-two sorted driver rows, one continuous mesh (no region modes)."""
    with pytest.raises(ValueError):
        DM.build(None, nx=4, lattice=dict(ys_um=[1.0, 2.0, 3.0], driver_rows=[0, 1, 2]))
    with pytest.raises(ValueError):
        DM.build(None, nx=4, lattice=dict(ys_um=[1.0, 2.0, 3.0], driver_rows=[1, 0]))
    with pytest.raises(ValueError):
        DM.build(None, nx=4, regions=1, lattice=dict(ys_um=[1.0, 2.0, 3.0], driver_rows=[0, 2]))


def test_leaf_grid_validation():
    """CLOCK-KV-R4 lattice leaf_grid: [nx = --nx, pow2 ny_leaf]; replaces driver_rows; no --plan-sites."""
    ys = [1.0, 2.0, 3.0]
    with pytest.raises(ValueError):
        DM.build(None, nx=4, lattice=dict(ys_um=ys, leaf_grid=[4, 6]))
    with pytest.raises(ValueError):
        DM.build(None, nx=4, lattice=dict(ys_um=ys, leaf_grid=[8, 8]))
    with pytest.raises(ValueError):
        DM.build(None, nx=4, lattice=dict(ys_um=ys, leaf_grid=[4, 8], driver_rows=[0, 1]))
    with pytest.raises(ValueError):
        DM.build(None, nx=4, plan_sites={}, lattice=dict(ys_um=ys, leaf_grid=[4, 8]))


def test_free_toward_and_poly_point():
    class K:
        def hit(self, x, y, m=0.0):
            return 0 <= x <= 50 and -5 <= y <= 5
    q, d = DM.free_toward(K(), (40.0, 0.0), 0, -100.0, 100.0)
    assert q is not None and q[0] < 0 and d > 40          # only toward the parent (x < 40)
    assert DM.free_toward(K(), (40.0, 0.0), 0, 100.0, 5.0) == (None, None)
    assert DM.poly_point([(0, 0), (0, 10), (5, 10)], 12) == (2.0, 10.0)


def test_bisection_congruent_explicit_leaf_lattice():
    """CLOCK-KV-R5 leaf_ys_um / xs_um: every bisection's upper half is a translate of the lower half (equal legs by
    construction); a gap between congruent partition-row groups passes, a non-translate or non-pow2 set fails."""
    p = 190.08
    gap = [p / 2 + p * j for j in range(4)] + [1000.0 + p / 2 + p * j for j in range(4)]
    assert DM.bisection_congruent([p / 2 + p * j for j in range(8)], "u")
    assert DM.bisection_congruent(gap, "gap")
    with pytest.raises(ValueError):
        DM.bisection_congruent(gap[:4] + [1000.0 + p / 2 + p * j for j in (0, 1, 2, 4)], "bad")
    with pytest.raises(ValueError):
        DM.bisection_congruent([1.0, 2.0, 3.0], "n3")
    with pytest.raises(ValueError):
        DM.bisection_congruent([2.0, 1.0], "order")


def test_band_plan_equal_structure():
    """CLOCK-KV-R6 band trees: taps outside the leaf-group cover go to the nearest group-edge leaf row on their nearest
    V strap; one h for every tree = half the deepest tap depth (site-rounded); a band too deep for one level fails."""
    p = 190.08
    ly = [p / 2 + p * j for j in range(4)] + [2000.0 + p / 2 + p * j for j in range(4)]
    xs = [100.0, 446.14]
    taps = [(110.0, 300.0), (120.0, 1200.0), (440.0, 1500.0), (430.0, 2650.0), (100.0, 2900.0)]
    B = DM.band_plan(ly, xs, taps, 480.0)
    assert set(B["taps"]) == {1, 2, 4}                       # 0 and 3 inside a group cover
    t1, t2, t4 = B["taps"][1], B["taps"][2], B["taps"][4]
    assert (t1["i"], t1["dir"], round(t1["edge_y"], 2)) == (0, 1, round(ly[3], 2))
    assert (t2["i"], t2["dir"], round(t2["edge_y"], 2)) == (1, -1, round(ly[4], 2))
    assert t4["dir"] == 1 and round(t4["edge_y"], 2) == round(ly[7], 2)
    dmax = max(v["depth"] for v in B["taps"].values())
    assert dmax / 2 <= B["h_um"] < dmax / 2 + DM.STEP_UM
    assert DM.band_plan(ly, xs, [taps[0], taps[3]], 480.0) is None
    with pytest.raises(ValueError):
        DM.band_plan(ly, xs, taps, 100.0)
