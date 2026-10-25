"""ft input hold cells from the plan (S81/FTHOLD 10-25, COORD 00:46 recipe): tools/die_plan/ft_hold.py.
    python3 -m pytest -q tools/die_plan/test_ft_hold.py"""
import copy
import gzip
import json
import os
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import face_guard  # noqa: E402
import ft_hold  # noqa: E402
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _on(raw, **kw):
    raw = copy.deepcopy(raw)
    raw["clock"]["ft_hop_in_share"] = 0.16
    raw["clock"]["ft_in_hold"] = "liberty"
    raw["clock"].update(kw)
    return raw


def _ft_type(P):
    return next(t for t in P.types if P.types[t].get("ft_slots") and any(p["type"] == t for p in P.parts.values()))


def test_need_and_chain_from_the_contract():
    """need = insertion_tol + half the hold uncertainty + face-flop FF hold - port buffer FF; the chain covers it by
    0..5 ps (FF min) with the least TT delay, <= 2 cells (face_flops.tcl finds station 0 through <= 2 buffers)."""
    P = schema.Plan(_on(PAIR))
    need = ft_hold.need_ps(P)
    assert need == pytest.approx(40 + 12.5 + ft_hold.TH_FF_PS - ft_hold.PORT_BUF_FF_PS)
    cells, ff, tt = ft_hold.chain(P)
    assert 1 <= len(cells) <= 2 and need <= ff <= need + ft_hold.WINDOW_PS
    best = tt
    # brute force: no other <= 2-cell chain in the window is faster at TT
    names = list(ft_hold.CELLS)
    for a in names:
        for b in [None] + names:
            c = [a] + ([b] if b else [])
            f = sum(ft_hold.CELLS[x][0] for x in c)
            t = sum(ft_hold.CELLS[x][1] for x in c)
            if need <= f <= need + ft_hold.WINDOW_PS:
                assert t >= best - 1e-9
    assert cells == ("HB3xp67_ASAP7_75t_R", "HB2xp67_ASAP7_75t_R")    # s81 contract: 52.94 ps FF / 87.65 ps TT


def test_pick_edges():
    assert ft_hold.pick(0) == ((), 0.0, 0.0)
    assert ft_hold.pick(14.0)[0] == ("HB1xp67_ASAP7_75t_R",)
    with pytest.raises(ft_hold.FtHoldError):
        ft_hold.pick(200.0)
    P = schema.Plan(_on(PAIR, ft_in_hold_ps=30.0))
    assert ft_hold.need_ps(P) == 30.0 and 30.0 <= ft_hold.chain(P)[1] <= 35.0


def test_off_by_default_changes_nothing():
    P = schema.Plan(PAIR)
    tn = _ft_type(P)
    assert not ft_hold.enabled(P) and ft_hold.chain(P) == ((), 0.0, 0.0) and ft_hold.module_text(P) == ""
    assert gen_phys.ft_hop_in_share(P) == gen_phys.FT_HOP_IN_SHARE
    txt = gen_rtl.wrapper(P, tn, gen_rtl.bus_epochs(P))
    assert "u_ftd_" not in txt and "ot_dp_dly" not in txt


def test_schema_field():
    assert schema.validate(_on(PAIR)) == []
    bad = _on(PAIR, ft_in_hold="maybe")
    assert schema.validate(bad)
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    clk = json.dumps(on_disk)
    assert "ft_in_hold" in clk and "ft_in_hold_ps" in clk


def test_sdc_share_hosts_the_cells_and_lints():
    """the receiver share grows by the chain's TT delay (no cycle added); kit SDC and sdc_lint floors agree; a kit made
    without the cells fails the lint of the plan with them (the sender's ft_o share is tighter)."""
    raw = _on(PAIR)
    P = schema.Plan(raw)
    tn = _ft_type(P)
    per = float(P.die["period_ps"])
    _c, _ff, tt = ft_hold.chain(P)
    sh = 0.16 + tt / per
    assert gen_phys.ft_hop_in_share(P) == pytest.approx(sh)
    txt = gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))
    assert f"set_input_delay -max {gen_phys.t_lib((1 - sh) * per):.4f}" in txt
    assert f"set_output_delay -max {gen_phys.t_lib(sh * per):.4f}" in txt
    assert "ft input hold cells" in txt
    # the signed-early hold contract is unchanged (no relaxation)
    assert f"set_input_delay -min {gen_phys.t_lib(-float(P.clock['insertion_tol_ps'])):.4f}" in txt
    assert sdc_lint.lint(txt, **sdc_lint.kit_context(P, tn)) == []
    off = copy.deepcopy(raw)
    off["clock"]["ft_in_hold"] = "off"
    old = gen_phys.sdc(schema.Plan(off), tn, gen_phys.type_pins(P, tn))
    assert sdc_lint.lint(old, **sdc_lint.kit_context(P, tn))


def test_rtl_chain_before_station0():
    raw = _on(PAIR)
    P = schema.Plan(raw)
    tn = _ft_type(P)
    ep = gen_rtl.bus_epochs(P)
    txt = gen_rtl.wrapper(P, tn, ep)
    mod = ft_hold.module_name(ft_hold.chain(P)[0])
    for s in P.types[tn]["ft_slots"]:
        n, W = gen_rtl.sv_id(s["name"]), s["width"]
        wi = W + (1 if ep.get((tn, s["name"] + "_i"), True) else 0)
        assert f"{mod} #(.W({wi})) u_ftd_{n} (.d({n}_i), .q({n}_ih));" in txt
        s0 = re.search(rf"u_ft_{n}_s0 \(([^;]*)\);", txt).group(1)
        assert f".d({n}_ih[{W - 1}:0])" in s0 and f"{n}_i[" not in s0
    cells = ft_hold.module_text(P)
    assert f"module {mod} " in cells and "`ifdef SYNTHESIS" in cells and "assign q = d;" in cells
    assert "(* keep *) HB3xp67_ASAP7_75t_R u0 (.A(d[i]), .Y(n0));" in cells
    assert "(* keep *) HB2xp67_ASAP7_75t_R u1 (.A(n0), .Y(q[i]));" in cells


def test_written_cells_file_and_face_keep(tmp_path):
    raw = _on(PAIR)
    files = gen_rtl.write_rtl(raw, tmp_path)
    cells = (tmp_path / "ot_dp_cells.sv").read_text()
    assert cells.startswith(gen_rtl.CELLS) and "ot_dp_dly_hb3_hb2" in cells and files
    keep = (HERE / "face_keep.tcl").read_text()
    rel = (HERE / "face_keep_release.tcl").read_text()
    assert "u_ftd_" in keep and "u_ftd_" not in rel
    # the release regex must not match a hold cell (they stay dont_touch for the whole flow)
    rx = re.search(r"regexp \{([^}]*)\}", rel).group(1)
    assert not re.search(rx, "u_ftd_ft2/g[0].u0")
    assert re.search(r"(^|[/.])u_ftd_[^/.]*[/.]", "u_ftd_ft2/g[0].u0")


def test_face_guard_accepts_the_chain():
    """station 0 stays the input's face register through the two hold cells (face_guard MAX_CHAIN)."""
    net = r"""
module top(clk, a, o);
  input clk; input [0:0] a; output [0:0] o;
  wire n0; wire n1; wire q; wire _0_;
  HB3xp67_ASAP7_75t_R \u_ftd_a.g[0].u0  (.A(a[0]), .Y(n0));
  HB2xp67_ASAP7_75t_R \u_ftd_a.g[0].u1  (.A(n0), .Y(n1));
  DFFHQNx1_ASAP7_75t_R \u_ft_a_s0.q[0]$_DFF_P_  (.CLK(clk), .D(n1), .QN(q));
  DFFHQNx1_ASAP7_75t_R \u_ft_a_s1.q[0]$_DFF_P_  (.CLK(clk), .D(q), .QN(_0_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));
endmodule
"""
    r = face_guard.guard(net, pins=[dict(bus="a", bit=0), dict(bus="o", bit=0)])
    assert r["verdict"] == "PASS", r


LIB = Path(os.environ.get("OT_ASAP7_LIB_DIR", "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"))


@pytest.mark.skipif(not (LIB / "asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz").exists(),
                    reason="ASAP7 Liberty not on this host (set OT_ASAP7_LIB_DIR or run in the ORFS image)")
def test_cell_delays_match_the_liberty():
    def cell(text, name):
        i = text.index("{", text.index(f"cell ({name})"))
        d, j = 0, i
        while True:
            d += {"{": 1, "}": -1}.get(text[j], 0)
            if d == 0:
                return text[i:j]
            j += 1

    def tbl(body, kind, s, ld):
        b = re.search(kind + r"\s*\([^)]*\)\s*\{(.*?)\}", body, re.S).group(1)
        i1 = [float(x) for x in re.search(r'index_1\s*\(\s*"([^"]*)"', b).group(1).split(",")]
        i2 = [float(x) for x in re.search(r'index_2\s*\(\s*"([^"]*)"', b).group(1).split(",")]
        v = [[float(x) for x in r.split(",")] for r in
             re.findall(r'"([^"]*)"', re.search(r"values\s*\((.*?)\)\s*;", b, re.S).group(1))]

        def seg(a, x):
            return next((k for k in range(len(a) - 1) if x <= a[k + 1]), len(a) - 2)
        a, c = seg(i1, s), seg(i2, ld)
        fa, fc = (s - i1[a]) / (i1[a + 1] - i1[a]), (ld - i2[c]) / (i2[c + 1] - i2[c])
        return ((1 - fa) * (1 - fc) * v[a][c] + (1 - fa) * fc * v[a][c + 1] + fa * (1 - fc) * v[a + 1][c]
                + fa * fc * v[a + 1][c + 1])
    ff = gzip.open(LIB / "asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz", "rt").read()
    tt = gzip.open(LIB / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz", "rt").read()
    for name, (fmin, tmax) in ft_hold.CELLS.items():
        bf, bt = cell(ff, name), cell(tt, name)
        assert min(tbl(bf, "cell_rise", 15, 0.6), tbl(bf, "cell_fall", 15, 0.6)) == pytest.approx(fmin, abs=0.05)
        assert max(tbl(bt, "cell_rise", 15, 0.9), tbl(bt, "cell_fall", 15, 0.9)) == pytest.approx(tmax, abs=0.05)
