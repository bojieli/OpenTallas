"""INFRA-FIRST-QC-R28: per-net PG cut-outs (net_holes_um) + pg_mesh_cut rules."""
from types import SimpleNamespace

import die_clock_mesh as D
import die_infra as I
import pg_mesh_cut as M

P = SimpleNamespace(W=86.4, H=86.4, layers={"M8": dict(dir="H"), "M9": dict(dir="V")})
ROW = dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"])
COL = dict(ROW, layer="M9")


def test_net_hole_cuts_only_that_net():
    g = [dict(ROW, net_holes_um={"VSS": [[10.0, 17.0, 30.0, 17.6]]}), COL]
    r = I.pg_rects(P, g)
    vss = sorted(x for x in r if x[0] == "VSS" and x[1] == "M8" and abs((x[3] + x[5]) / 2 - 17.28) < 1e-6)
    assert [(round(x[2], 3), round(x[4], 3)) for x in vss] == [(0.0, 10.0), (30.0, 86.4)]
    assert len([x for x in r if x[0] == "VDD"]) == len([x for x in I.pg_rects(P, [ROW, COL]) if x[0] == "VDD"])


def test_mesh_holes_keepout_and_continuity():
    nd = D.NDR["8w"]
    mesh = dict(M8=[dict(y=17.28, x0=20.0, x1=50.0), dict(y=17.28, x0=49.0, x1=60.0)], M9=[])
    holes, meta = M.mesh_holes(mesh, nd)
    assert meta["runs"]["M8"] == 1 and len(holes["M8"]) == 1
    h = holes["M8"][0]
    assert abs(h[0] - (20.0 - 0.64)) < 1e-6 and abs(h[2] - (60.0 + 0.64)) < 1e-6
    g = M.apply_holes([ROW, COL], holes)
    r = I.pg_rects(P, g)
    c = M.continuity(r, "VSS", cut_pitch=8.64, orig=I.pg_rects(P, [ROW, COL]))
    assert c["components"] == 1 and c["floating_m8"] == 0 and c["dangling_end_m8"] == 0


def test_floating_piece_detected():
    g = [dict(ROW, net_holes_um={"VSS": [[0.0, 17.0, 80.0, 17.6]]}), COL]
    r = I.pg_rects(P, g)
    fl = M.continuity_floating(r, "VSS", "M8")
    assert len(fl) == 1 and fl[0][0] >= 80.0 - 1e-6     # the 80..86.4 tail crosses no VSS column (86.4 off-die)


def test_pair_spacing_wide_pair_and_pdngen_spacing():
    """R28 wide grid: VDD at offset, VSS at offset + width + pair_spacing, one wide gap per pitch (same in tcl)."""
    import pg_regions as R
    row = dict(layer="M8", width_um=1.92, pitch_um=8.64, offset_um=2.86, nets=["VDD", "VSS"], pair_spacing_um=1.0)
    r = sorted(x for x in I.pg_rects(P, [row]) if x[3] < 8.64)
    assert [(x[0], round(x[3], 3), round(x[5], 3)) for x in r] == [("VDD", 1.9, 3.82), ("VSS", 4.82, 6.74)]
    gap = 8.64 + 1.9 - 6.74
    assert abs(gap - 3.80) < 1e-9                       # clock gap centred on the 0 mod 8.64 strap lane
    spec = R.row_spec(row, tuple(R._d(v) for v in (0.0, 0.0, 86.4, 86.4)), ["VDD", "VSS"])
    assert "-spacing 1" in R.stripe_tcl("{top}", spec) and "-starts_with POWER" in R.stripe_tcl("{top}", spec)


def test_router_wide_pg_spacing():
    """R28: an 8w clock wire must keep the 1.0 um wide-table spacing from a 1.92 um PG stripe (NDR space 0.08 alone
    is not enough); a narrow 0.48 PG stripe keeps the NDR space."""
    import die_clock_128 as C
    ix = C.MetalIndex(0.08)
    ix.add(("M8", "VDD", "pg", 10.0, 11.92, 0.0, 100.0))
    ix.add(("M8", "VSS", "pg", 20.0, 20.48, 0.0, 100.0))
    assert ix.hits(("M8", "ck", "clk", 12.5, 12.82, 0.0, 50.0), first=True)          # 0.58 < 1.0
    assert not ix.hits(("M8", "ck", "clk", 12.92, 13.24, 0.0, 50.0), first=True)     # 1.00
    assert not ix.hits(("M8", "ck", "clk", 12.5, 12.82, 0.0, 1.5), first=True)       # PRL 1.5 < 1.8
    assert not ix.hits(("M8", "ck", "clk", 19.6, 19.92, 0.0, 50.0), first=True)      # 0.08 to a 0.48 stripe


def test_m8_branch_flush_with_via89_array():
    """QC-MESH-R25 Min Step: a 0.187 um M8 branch out of the 6x6 VIA89 array (M8 +-0.265) ends flush with the array
    edge (ext 0.078, was 0.08 -> 2-nm step); larger mismatches (no DRC marker in R25) keep the R19 extension."""
    import clock_routed as CR
    CR._V89_M8_HALF[0] = CR.via89_m8_half(dict(rows=6, cols=6, cut=0.04, pitch=0.098, enc_m8=0.0))
    try:
        L = []
        CR._emit_steps(L, [("M9", 2204.44, 10749.24), ("M8", 2204.44, 10749.24), ("M8", 2204.253, 10749.24),
                           ("M7", 2204.253, 10749.24)], m8_end_ext=0.08)
        assert "$e addPoint 2204253 10749240 78" in L
        L = []
        CR._emit_steps(L, [("M9", 0.0, 0.0), ("M8", 0.0, 0.0), ("M8", 0.243, 0.0), ("M7", 0.243, 0.0)], m8_end_ext=0.08)
        assert "$e addPoint 243 0 80" in L
    finally:
        CR._V89_M8_HALF[0] = None
