"""qc_clk_mesh3 r10 regressions: solve times the LEGALIZED cells (units expanded, pin-to-pin nets), not the ideal plan
legs (QC-CLK-MESH-3 gap diagnosed by CODEX 10-26 20:57: 427 bumps / 8.64 + 4.32 um lanes missing from variation)."""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qc_clk_mesh3 as M  # noqa: E402


class FakeStage:
    """linear stage: 30 ps + 0.1 ps/um, sigma 2 ps, slew 100 + 0.4/um."""

    def seg(self, w, m, c, L):
        return 30.0 + 0.1 * L

    def sigma(self, w, m, c, L):
        return 2.0

    def slew(self, w, m, c, L):
        return 100.0 + 0.4 * L


def tiny(block_rep=True):
    st = FakeStage()
    top = M.EdgeType(st, "16w", 2, 450.0)
    col = M.EdgeType(st, "4w", 1, 450.0)
    # top tree: root T (100, 900) -> leaf t0 (100, 0) = column tap; 900 um, 2 stages (1 repeater at y 450)
    T = dict(tag="T", xy=(100.0, 900.0), kids=["t0"], T={"TT": 0, "FF": 0}, S=0, parent=None)
    t0 = dict(tag="t0", xy=(100.0, 0.0), kids=[], T={"TT": 0, "FF": 0}, S=0, parent="T", leg=900.0, nseg=2, et=top)
    # column tree: tap c_tap (100, 0) -> two fine drivers (100, -300) / (100, 300), 1 stage each
    ct = dict(tag="c_tap", xy=(100.0, 0.0), kids=["c_a", "c_b"], T={"TT": 0, "FF": 0}, S=0, parent=None)
    ca = dict(tag="c_a", xy=(100.0, -300.0), kids=[], parent="c_tap", leg=300.0, nseg=1, et=col)
    cb = dict(tag="c_b", xy=(100.0, 300.0), kids=[], parent="c_tap", leg=300.0, nseg=1, et=col)
    cores = [(1000.0, -2000.0, 1200.0, 2000.0)]           # far right: tree lanes go left (wider side ... left of x=100 is 0)
    blk = (lambda q: 430.0 <= q[1] <= 470.0) if block_rep else (lambda q: False)
    B = dict(top_nodes=[T, t0], cnodes=[ct, ca, cb], ctrees=[dict(g=0, c=0, tap=(100.0, 0.0), root="c_tap", nodes=[ct, ca, cb])],
             cores=cores, added_cols=[], incore=blk, et=dict(top=top, col=col))
    return B


def test_decompose_real_cells():
    assert M.decompose(1.0) == ["BUFx24"]
    assert M.decompose(1.334) == ["BUFx16f", "BUFx16f"]
    assert M.decompose(2.0) == ["BUFx24", "BUFx24"]
    assert sorted(M.decompose(3.334)) == sorted(["BUFx24", "BUFx24", "BUFx16f", "BUFx16f"])
    assert M.decompose(4.0) == ["BUFx24"] * 4
    for m in (0.5, 0.667, 1.0, 1.5, 1.667, 2.0):         # every d1 MULT_SET x base 1 / 2 decomposes
        for base in (1.0, 2.0):
            cells = M.decompose(round(m * base, 3))
            assert abs(sum(M.BUF_STRENGTH[c] for c in cells) - m * base) <= 0.011


def test_phys_edges_use_legal_sites_not_ideal_legs():
    B = tiny(block_rep=True)
    cells, st = M.legalize(B, {(100.0, -300.0): ["BUFx24"] * 4})
    B["cells"] = cells
    PE = M.phys_edges(B)
    top = PE[("t", "t0")]
    assert len(top) == 2                                    # nseg pieces: T -> rep -> column-tap cell
    rep = cells[B["site_of"][("top_rep", "t0", 1)]]
    bump = rep["site"][1] - 450.0
    assert st["bumped"] >= 1 and abs(bump) > 10.0           # the blocked repeater moved off its ideal site
    L1, L2 = top[0][2], top[1][2]
    # the legal pieces carry the bump (ideal model: 450 / 450)
    assert abs(L1 - (450.0 - bump)) < 3.0 and abs(L2 - (450.0 + bump)) < 3.0  # includes true LEF pin offsets
    assert abs(L1 - 450.0) > 10.0
    # the merged level: top leaf == column-tap cell (one cell)
    assert B["site_of"][("t", "t0")] == B["site_of"][("c", "c_tap")]
    # units expanded: the 4-unit fine driver ties 3 rows; its net = pin-to-pin + tie, with the 8.64 lane jog
    (_, _, La), = PE[("c", "c_a")]
    fa = cells[B["site_of"][("c", "c_a")]]
    assert fa["units"] == 4 and fa["masters"] == ["BUFx24"] * 4
    (pa, tie) = M.pin_xy(fa, "A")
    assert abs(tie - 3 * M.ROW_H) < 1e-9
    assert La > 300.0 + M.DX_LANE - 2.0                       # lane offset of the column tap is in the net
    assert st["instances"] == sum(c["units"] for c in cells)


def test_pin_model_from_lef():
    c = dict(site=[10.0, 5.0], masters=["BUFx24"])
    (a, _), (y, _) = M.pin_xy(c, "A"), M.pin_xy(c, "Y")
    assert abs((y[0] - a[0]) - (1.593 - 0.027)) < 1e-9       # A left edge, Y bar centre (asap7 R 1x LEF)
    assert abs(a[1] - 4.995) < 1e-9


def test_r9_inputs_parse():
    d = HERE.parent.parent / "results/qc_clk_mesh3/r10_inputs"
    if not (d / "r9_lattice.json").exists():
        return
    R = M.load_r9(d)
    leaves = [t for t, n in R["nodes"].items() if n["depth"] == 4]
    assert len(leaves) == 16
    tt = [R["rcx"]["TT"][t]["late"] for t in leaves]
    assert math.isclose(max(tt) - min(tt), 21.697, abs_tol=0.01)   # tree5 summary TT spread


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("PASS", k)


class FakePlan:
    """two instances of one partition type (R0 + MX, stacked) with one hard core each, + a narrow second type."""

    def __init__(self):
        self.W, self.H = 2000.0, 2000.0
        self.parts = {"a0": dict(type="A", origin_um=[0.0, 0.0], orient="R0"),
                      "a1": dict(type="A", origin_um=[0.0, 1000.08], orient="MX"),
                      "b0": dict(type="B", origin_um=[1000.08, 0.0], orient="R0")}
        self.size = {"A": (1000.08, 1000.08), "B": (500.04, 1000.08)}

    def rect(self, n):
        x0, y0 = self.parts[n]["origin_um"]
        w, h = self.size[self.parts[n]["type"]]
        return (x0, y0, x0 + w, y0 + h)


def islands():
    P = FakePlan()
    # core of type A at type-frame (100..400, 100..300): die frame R0 as is, MX mirrored in y inside a1
    cores = [(100.0, 100.0, 400.0, 300.0, "a0", "u", "m"), (100.0, 1000.08 + 1000.08 - 300.0, 400.0, 1000.08 + 1000.08 - 100.0, "a1", "u", "m")]
    return P, M.Islands(P, cores, pitch=50.0, pitch_x=20.0)


def test_islands_identical_per_type_and_off_core():
    P, I = islands()
    gx, gy, ok = I.tgrid["A"]
    assert I.types["A"]["slots"] < I.types["A"]["grid"]          # the core removed slots
    for n in ("a0", "a1"):
        x0, y0, x1, y1 = P.rect(n)
        for k in range(len(gx)):
            for j in range(len(gy)):
                if not ok[k, j]:
                    continue
                ox, oy = I.to_die(n, float(gx[k]), float(gy[j]))
                assert x0 <= ox and ox + I.CW <= x1 and y0 <= oy and oy + I.BH <= y1      # body in ONE partition
                for c in ([(100.0, 100.0, 400.0, 300.0)] if n == "a0" else [(100.0, 1700.16, 400.0, 1900.16)]):
                    assert not (ox < c[2] and c[0] < ox + I.CW and oy < c[3] and c[1] < oy + I.BH)
    # the grid is symmetric: MX maps it onto itself (identical type-frame slot set on both instances)
    h = P.size["A"][1]
    assert sorted(round(h - I.BH - v, 3) for v in gy) == sorted(round(v, 3) for v in gy)
    assert all(abs(round(v / 0.27) * 0.27 - v) < 1e-6 for v in gy) and all(abs(round(v / 0.054) * 0.054 - v) < 1e-6 for v in gx)


def test_islands_row_uses_one_slot_row_per_partition():
    P, I = islands()
    xs, m = I.row_x(500.0)
    assert xs and len({round(m[x], 3) for x in xs if x < 1000.0}) == 1
    # a row on the a0/a1 seam takes the partition HOLDING the line (the upper one, a1)
    xs2, m2 = I.row_x(1000.08)
    assert all(m2[x] > 1000.08 for x in xs2 if x < 1000.0)
    # snapped chain: segments stay within reach - margin
    st = FakeStage()
    et = M.EdgeType(st, "16w", 2, 450.0)
    I.et = et
    n = M.nseg_snap(I, et, "x", 500.0, xs[0], xs[-1])
    assert I.chain_max_seg("x", 500.0, xs[0], xs[-1], n) <= 450.0 - I.margin + 1e-6


# ------------------------------------------------------------------------------------------------ INFRA-FIRST-HEAD-2
def test_qc_defaults_unchanged():
    """the QC lattice constants stay the defaults; set_lattice() with no per-die flag restores exactly them."""
    import argparse
    assert M.QC_LATTICE == dict(PER_X=2471.04, PER_OFF=(0.0, 622.08, 1235.52, 1848.96), CHAN_HC=2,
                                CHAN_LANES=(0, 4, 1, 3), PER_NUDGE=8.64, ROW_GROUP=19)
    got = M.set_lattice(argparse.Namespace())
    assert got == M.QC_LATTICE
    assert (M.PER_X, M.PER_OFF, M.CHAN_HC, M.CHAN_LANES, M.PER_NUDGE, M.ROW_GROUP) == tuple(M.QC_LATTICE.values())


def test_qc_defaults_explicit_flags_parse_identical():
    """the QC values passed explicitly as CLI strings parse to the identical constants (types included)."""
    p = M.argparse.ArgumentParser()
    M.add_common(p)
    a = p.parse_args(["--r2", "x", "--stage", "y", "--per-x", "2471.04", "--per-off", "0.0,622.08,1235.52,1848.96",
                      "--chan-hc", "2", "--chan-lanes", "0,4,1,3", "--per-nudge", "8.64", "--row-group", "19"])
    got = M.set_lattice(a)
    assert got == M.QC_LATTICE and all(type(got[k]) is type(v) for k, v in M.QC_LATTICE.items())
    assert all(type(x) is float for x in got["PER_OFF"]) and all(type(x) is int for x in got["CHAN_LANES"])
    a2 = p.parse_args(["--r2", "x", "--stage", "y", "--per-x", "1000"])
    assert M.set_lattice(a2)["PER_X"] == 1000.0
    M.set_lattice(M.argparse.Namespace())          # restore QC
    assert M.PER_X == 2471.04


def test_grid_tree_non_power_of_two_balanced():
    """head form: 11 x 12 drivers per half (22 x 12 die rows), not a power of two -> one stage count and zero
    nominal skew by construction (linear stage model)."""
    st = FakeStage()
    et = M.EdgeType(st, "16w", 2, 450.0)
    xs = [354.24 + 708.48 * i for i in range(11)]
    xs += [17521.92 - x for x in xs]                 # E half = mirror of the W half about the die centre
    ys = [876.96 + 1036.8 * j for j in range(12)]
    drv = [(x, y) for y in ys for x in xs]
    nodes, root, info = M.grid_tree(drv, et, root=(8760.96, 8778.24))
    rep, arr = M.grid_report(nodes, root)
    assert rep["drivers"] == 264 and info["rows"] == 12 and info["cols_per_row"] == [22] and not info["lifted_rows"]
    assert len(rep["stages"]) == 1
    assert rep["arrival_ps"]["TT"]["skew"] <= 0.5, rep["arrival_ps"]       # 1-um node step resolution x depth
    assert rep["all_straight"]


def test_grid_tree_odd_counts():
    """3 x 5 grid (odd both ways): every driver reached, equal stages, balanced."""
    st = FakeStage()
    et = M.EdgeType(st, "16w", 2, 450.0)
    drv = [(100.0 * i, 200.0 * j) for i in range(3) for j in range(5)]
    nodes, root, info = M.grid_tree(drv, et)
    rep, _ = M.grid_report(nodes, root)
    assert rep["drivers"] == 15 and len(rep["stages"]) == 1 and rep["arrival_ps"]["TT"]["skew"] <= 0.5


def test_stacked_units_share_same_pg_rail_and_transform_access():
    c = dict(site=[10., 1.215], masters=["BUFx24"] * 2)
    us = M.unit_sites(c)
    assert [u["orient"] for u in us] == ["R0", "MX"]
    assert us[1]["origin_um"][1] - us[0]["origin_um"][1] == M.ROW_H
    # LEF VDD [.261,.279] of lower R0 equals VDD [-.009,.009]
    # after mirroring upper MX about its .27um row centre.
    low = us[0]["origin_um"][1]
    high = us[1]["origin_um"][1]
    assert all(abs(a-b)<1e-9 for a,b in zip((low+.261,low+.279),(high-.009,high+.009)))
    a0 = M.unit_pin(c,0,"A",access=True)
    a1 = M.unit_pin(c,1,"A",access=True)
    assert abs(a0[1]-(low+.09))<1e-9
    assert abs(a1[1]-(high+.18))<1e-9


def test_r33_col_lane_side_mirrors():
    """R33: the column-tree lane side is the wider channel side; a W/E mirrored core pair gives mirrored signs."""
    import qc_clk_mesh3 as M
    cores = [(0.0, 0.0, 90.0, 10.0), (130.0, 0.0, 200.0, 10.0)]          # channel 90..130, column at 100 -> east wider
    assert M.col_lane_side(cores, 100.0) == 1.0
    mir = [(200.0 - c[2], c[1], 200.0 - c[0], c[3]) for c in cores]       # mirror about x = 100
    assert M.col_lane_side(mir, 100.0) == -1.0
