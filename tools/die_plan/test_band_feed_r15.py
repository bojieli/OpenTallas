#!/usr/bin/env python3
"""CLOCK-KV-R15 unit tests: band_root_reach_um, strap_cover, band_feed leaf (die_clock_mesh) and the shared CLK-AOCV
mesh walk (die_clock_128.mesh_walk_nets / aocv_fold_fields mesh_walk).  python3 -m pytest tools/die_plan/test_band_feed_r15.py"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as CM  # noqa: E402
import die_clock_128 as C128  # noqa: E402


class Box:
    """keep-out index stand-in: blocked rects (x0, y0, x1, y1)."""
    def __init__(self, *r):
        self.r = list(r)

    def hit(self, x, y, m=0.0):
        return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, y0, x1, y1 in self.r)


def _fixture(K=None, feed="mesh", root_reach=0.0):
    """one V strap x=100, leaf rows 0..200 (pitch 100), two band taps above the last row (y 260, 300)."""
    xs, ly = [100.0], [0.0, 100.0, 200.0]
    taps = [(100.0, 260.0), (100.0, 300.0)]
    BT = CM.band_plan(ly, xs, taps, hop_max=600.0)
    cells, nets = {}, []

    def cell(name, x, y, kind, **kw):
        cells[name] = dict(x=x, y=y, kind=kind, **kw)
        return name
    out = dict(meta={}, pushdown=[], unplaced=[],
               drivers={f"0_{j}": dict(site=[100.0, y], cells=[f"ckm_d_0_{j}_0", f"ckm_d_0_{j}_1"])
                        for j, y in enumerate(ly)})
    nets.append(dict(name="ckm_w_ckm_n2_h1", drv="ckm_n2_h1", loads=["ckm_d_0_2_0", "ckm_d_0_2_1"], level=2))
    rows = []
    for k, (x, y) in enumerate(taps):
        sb = cell(f"ckm_s_{k}", x, y, "stub")
        nets.append(dict(name=f"ckm_w_{sb}", drv=sb, loads=[f"port:t{k}"], level=99))
        rows.append(dict(port=f"t{k}", stub=sb, foot=[x, y], xy=[x, y], band_tree=BT["taps"][k]["tree"]))
    CM.band_trees(BT, rows, cells, nets, K or Box((-9, -9, -8, -8)), xs, ly, cell, out, 600.0, root_reach=root_reach,
                  feed=feed)
    return BT, rows, cells, nets, out


def test_band_plan_half_depth_from_geometry():
    BT, *_ = _fixture()
    assert BT["h_um"] == pytest.approx(51.84)          # ceil(100 / 2 / 2.16) * 2.16: deepest band tap 100 um past y=200
    assert set(BT["taps"]) == {0, 1}


def test_band_feed_mesh_default_root_branch():
    _, rows, cells, nets, out = _fixture()
    r = out["band_roots"][0]
    assert cells[r["root"]]["kind"] == "broot" and cells[r["branch"]]["kind"] == "bnode"
    assert out["meta"]["band_trees"]["feed"] == "mesh" and out["meta"]["band_trees"]["stages_below_leaf_node"] == 4
    assert "ckm_br_0" not in nets[0]["loads"]                      # mesh-fed: the root is not on the tree net


def test_band_feed_leaf_equal_stage():
    _, rows, cells, nets, out = _fixture(feed="leaf")
    r = out["band_roots"][0]
    assert r["branch"] is None and r["feed"] == "leaf" and r["leaf_driver"] == "0_2"
    assert cells[r["root"]]["kind"] == "bleaf"
    leaf = nets[0]
    assert leaf["loads"][-1] == r["root"]                         # peer of the edge leaf's mesh driver cells
    root_net = [n for n in nets if n["drv"] == r["root"]]
    assert len(root_net) == 1 and sorted(root_net[0]["loads"]) == ["ckm_s_0", "ckm_s_1"]   # no branch stage
    assert not any(c["kind"] == "bnode" for c in cells.values())
    dep, _ = C128.stage_depths([dict(name="root", drv="port:root", loads=["ckm_n2_h1"])] + nets)
    # band stub = node + root + stub (3); a mesh-fed stub would be node + driver + stub (3) via the mesh walk
    assert dep["ckm_s_0"] == 3
    assert out["meta"]["band_trees"]["cells"] == 1 and r["trunk_um"] == pytest.approx(100.0)


def test_band_root_reach_slides_along_own_strap_past_core():
    # a multi-instance core covers the driver site (100, 200) up to y=230: without reach the root is STRUCTURAL
    K = Box((80.0, 150.0, 120.0, 230.0))
    _, _, _, _, out = _fixture(K=K)
    assert any("STRUCTURAL band_root" in u[1] for u in out["unplaced"])
    _, _, cells, _, out = _fixture(K=K, root_reach=60.0)
    r = out["band_roots"][0]
    assert not [u for u in out["unplaced"] if "band_root" in u[1]]
    assert r["foot"][0] == 100.0                                  # same V strap
    assert 230.0 < r["foot"][1] <= 200.0 + 60.0 + 1e-6           # moved toward the band, first free site past the edge
    assert r["root_slide_um"] == pytest.approx(r["foot"][1] - 200.0)


def test_strap_cover_spans_driven_area_only():
    xs = [0.0, 100.0]
    ly = [10.0, 20.0, 30.0, 70.0, 80.0]                          # gap 30 -> 70 splits two groups (pitch 10)
    ys = [0.0, 25.0, 50.0, 75.0, 95.0]
    spans, meta = CM.strap_cover_spans(xs, ys, ly)
    assert meta["cover_um"] == [[5.0, 35.0], [65.0, 85.0]]
    assert meta["m8_removed"] == [0, 2, 4]                       # y 0 / 50 / 95 lie outside every driven cover
    assert spans["H:1:None"] == [0.0, 100.0] and spans["H:2:None"] is None
    assert meta["m9_span_um"] == [10.0, 80.0]                    # M9 from the lowest to the highest driver row
    assert spans["V:0:None"] == spans["V:1:None"] == [10.0, 80.0]


def test_mesh_walk_counts_through_multi_driver_mesh():
    nets = [dict(name="root", drv="port:root", loads=["n0"]),
            dict(name="w_n0", drv="n0", loads=["n1a", "d_b"]),
            dict(name="w_n1a", drv="n1a", loads=["d_a"]),
            dict(name="w_s0", drv="s0", loads=["port:t0"]), dict(name="w_s1", drv="s1", loads=["port:t1"])]
    place = {"n0": dict(kind="node"), "n1a": dict(kind="node"), "d_a": dict(kind="drv"), "d_b": dict(kind="drv"),
             "s0": dict(kind="stub"), "s1": dict(kind="stub")}
    with pytest.raises(ValueError):
        C128.stage_depths(nets)[0]["s0"]                         # default: no path through the mesh
    mw = C128.mesh_walk_nets(nets, place)
    assert len(mw) == 1 and sorted(mw[0]["drv"]) == ["d_a", "d_b"] and sorted(mw[0]["loads"]) == ["s0", "s1"]
    dep, _ = C128.stage_depths(nets + mw)
    assert dep["d_a"] == 3 and dep["d_b"] == 2 and dep["s0"] == 4    # deepest mesh driver + 1
    M = dict(taps=[dict(port="t0", xy=[0, 0]), dict(port="t1", xy=[5, 5])])
    place.update({k: dict(place[k], x=1.0, y=2.0) for k in place})
    taps, nodes = C128.aocv_fold_fields(M, nets, place, {"n0": (10.0, 9.0, 5.0)}, mesh_walk=True)
    assert taps["t0"]["stages_from_root"] == 4 and nodes["h"]["stages"] == 1 if "h" in nodes else True


def test_mesh_walk_no_driver_raises():
    with pytest.raises(ValueError):
        C128.mesh_walk_nets([], {"s0": dict(kind="stub")})


def test_read_tree_band_root_lines(tmp_path):
    f = tmp_path / "tree_TT.txt"
    f.write_text("D ckm_d_0_0_0 10 9 30\nB ckm_br_0 11 10 31\nN ckm_n0 1 1 20\n")
    D, N = CM.read_tree(f)
    assert D["ckm_br_0"] == (11.0, 10.0, 31.0) and "ckm_br_0" not in N and "ckm_n0" in N
