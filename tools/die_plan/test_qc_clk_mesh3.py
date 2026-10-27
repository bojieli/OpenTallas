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
    assert abs(L1 - (450.0 - bump)) < 2.0 and abs(L2 - (450.0 + bump)) < 2.0
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
    assert abs((y[0] - a[0]) - (0.956 - 0.048)) < 1e-9       # A left edge, Y bar centre (asap7 R 1x LEF)
    assert abs(a[1] - (5.0 + M.ROW_H / 2)) < 1e-9


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
