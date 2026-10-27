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
