"""face_guard (CP1-R10, COORD 10-24): every planned face register survives Yosys as its own flop.
    python3 -m pytest -q tools/die_plan/test_face_guard.py"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import face_guard  # noqa: E402
import gen_rtl  # noqa: E402

NET_OK = r"""
module top(clk, a, o);
  input clk; input [1:0] a; output [1:0] o;
  wire _0_; wire _1_; wire [1:0] q;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[0]$_DFF_P_  (.CLK(clk), .D(a[0]), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[1]$_DFF_P_  (.CLK(clk), .D(a[1]), .QN(q[1]));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[0]$_DFF_P_  (.CLK(clk), .D(q[0]), .QN(_0_));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[1]$_DFF_P_  (.CLK(clk), .D(q[1]), .QN(_1_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));
  INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));
endmodule
"""


def test_handwritten_pass():
    r = face_guard.guard(NET_OK, pins=[dict(bus="a", bit=0), dict(bus="a", bit=1), dict(bus="o", bit=0),
                                       dict(bus="o", bit=1)])
    assert r["verdict"] == "PASS" and r["ok"] == 4, r


@pytest.mark.parametrize("clock_name", ["clk", "clk_t0", "clk_c2"])
def test_planned_clock_matches_netlist_skip(clock_name):
    net = NET_OK.replace("clk", clock_name)
    pins = [dict(bus=b, bit=i) for b in ("a", "o") for i in range(2)]
    pins.append(dict(bus=clock_name, bit=None, clock=True))
    r = face_guard.guard(net, pins=pins)
    assert r["verdict"] == "PASS" and r["planned_bits"] == 4, r
    missing = face_guard.guard(net, pins=pins + [dict(bus="absent", bit=0)])
    assert missing["fail_counts"].get("missing_port") == 1, missing
    assert missing["missing_ports"] == 1 and missing["planned_bits"] == 5, missing


def test_planned_pin_uses_custom_skip_expression():
    net = NET_OK.replace("clk", "special_clock")
    pins = [dict(bus=b, bit=i) for b in ("a", "o") for i in range(2)]
    r = face_guard.guard(net, pins=pins + [dict(bus="special_clock", bit=None)],
                         skip_re=r"^special_clock$")
    assert r["verdict"] == "PASS" and r["planned_bits"] == 4, r


def test_handwritten_failure_classes():
    merged = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "INVx3_ASAP7_75t_R _3_ (.A(_0_), .Y(o[1]));")
    assert "shared" in face_guard.guard(merged)["fail_counts"]
    dropped = NET_OK.replace(".D(a[1])", ".D(q[0])")
    assert "dropped" in face_guard.guard(dropped)["fail_counts"]
    const = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "assign o[1] = 1'b0;")
    assert "const" in face_guard.guard(const)["fail_counts"]
    feed = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "assign o[1] = a[1];")
    assert "feedthrough" in face_guard.guard(feed)["fail_counts"]
    comb = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "NAND2x1_ASAP7_75t_R _3_ (.A(_1_), .B(_0_), .Y(o[1]));")
    assert face_guard.guard(comb)["verdict"] == "FAIL"
    two = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));",
                         "INVx3_ASAP7_75t_R _3_ (.A(_0_), .Y(o[1]));\n  INVx3_ASAP7_75t_R _4_ (.A(_1_), .Y(o[1]));")
    assert face_guard.guard(two)["verdict"] == "FAIL"
    r = face_guard.guard(NET_OK, pins=[dict(bus="b", bit=0)])
    assert r["fail_counts"].get("missing_port") == 1


TOP = """
module top(input wire clk, input wire rst_n, input wire [1:0] a, input wire [1:0] unused_in,
           output wire [1:0] o1, output wire [1:0] o2, output wire [1:0] o3, output wire [2:0] o4);
  wire [1:0] x, aq; wire xe, ae;
  ot_dp_st #(.W(2)) u_bin_a (.clk(clk), .rst_n(rst_n), .d(a), .ea(rst_n), .q(aq), .eq(ae));
  ot_dp_st #(.W(2)) u_bout_o1 (.clk(clk), .rst_n(rst_n), .d(aq), .ea(rst_n), .q(o1), .eq());
  ot_dp_st #(.W(2)) u_bout_o2 (.clk(clk), .rst_n(rst_n), .d(aq), .ea(rst_n), .q(o2), .eq());
  ot_dp_st #(.W(2)) u_bout_o3 (.clk(clk), .rst_n(rst_n), .d(2'b01), .ea(rst_n), .q(o3), .eq());
  ot_dp_st #(.W(2)) u_bin_u (.clk(clk), .rst_n(rst_n), .d(unused_in), .ea(rst_n), .q(x), .eq(xe));
  ot_dp_ste #(.W(2)) u_bout_o4 (.clk(clk), .rst_n(rst_n), .d(aq), .ea(rst_n), .q(o4[1:0]), .eq(o4[2]));
endmodule
"""


def _synth(cells):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "c.v").write_text(cells + TOP)
        subprocess.run(["yosys", "-q", "-p", f"read_verilog {d}/c.v; synth -flatten -top top; opt -purge; "
                        f"write_verilog -noattr -noexpr {d}/n.v"], check=True, capture_output=True, timeout=300)
        return (Path(d) / "n.v").read_text()


@pytest.mark.skipif(not shutil.which("yosys"), reason="no yosys")
def test_yosys_keep_attributes_prevent_merges():
    """gen_rtl.CELLS (keep_hierarchy, keep): fan-out, constant-D and unused-q boundary flops all survive; without
    the attributes Yosys merges / removes them and the guard FAILs."""
    r = face_guard.guard(_synth(gen_rtl.CELLS), skip_re=r"^(clk|rst_n)$")
    assert r["verdict"] == "PASS" and r["ok"] == 13, r
    bare = gen_rtl.CELLS.replace("(* keep_hierarchy, keep *)\n", "").replace("(* keep_hierarchy *)\n", "")
    r = face_guard.guard(_synth(bare), skip_re=r"^(clk|rst_n)$")
    assert r["verdict"] == "FAIL", r
    assert {"dropped", "const"} <= set(r["fail_counts"]) and ({"shared", "merged", "feedthrough"} & set(r["fail_counts"]))


def test_kit_keeps_face_registers_through_eliminate_dead_logic():
    """CP1-R10 r10b: ORFS eliminate_dead_logic (synth_odb.tcl) deleted 120 unused-q face flops after Yosys kept them:
    the kit sets dont_touch on the boundary cells around that step and guards the 1_synth.odb netlist too."""
    import json
    import gen_phys
    import schema
    P = schema.Plan(json.loads((HERE / "examples" / "tiny_plan.json").read_text()))
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(P, "src", d, [])
        cfg = (kd / "config.mk").read_text()
        assert "export PRE_SYNTH_TCL = /work/face_keep.tcl" in cfg and "export POST_SYNTH_TCL = /work/face_keep_release.tcl" in cfg
        assert "set_dont_touch" in (kd / "face_keep.tcl").read_text()
        assert "unset_dont_touch" in (kd / "face_keep_release.tcl").read_text()
    assert "face_guard_odb.json" in gen_phys.RUN_KIT and "1_synth.odb" in gen_phys.RUN_KIT

NET_FT1 = r"""
module top(clk, ft0_i, ft0_o, ft1_i, ft1_o);
  input clk; input [1:0] ft0_i; output [1:0] ft0_o; input ft1_i; output ft1_o;
  DFFHQNx1_ASAP7_75t_R \u_ft_ft0_s0.q[0]$_DFF_P_  (.CLK(clk), .D(ft0_i[0]), .QN(ft0_o[0]));
  DFFHQNx1_ASAP7_75t_R \u_ft_ft0_s0.q[1]$_DFF_P_  (.CLK(clk), .D(ft0_i[1]), .QN(ft0_o[1]));
  DFFHQNx1_ASAP7_75t_R \u_ft_ft1_s0.q[0]$_DFF_P_  (.CLK(clk), .D(ft1_i), .QN(ft1_o));
endmodule
"""


def test_one_station_ft_slot_shares_its_register(tmp_path):
    """ELEM-S81 10-24: a 1-station ft slot's single station register is both its in- and out-face register."""
    assert face_guard.guard(NET_FT1)["verdict"] == "FAIL"                       # without the slot table: merged
    r = face_guard.guard(NET_FT1, ft1={"ft0", "ft1"})
    assert r["verdict"] == "PASS" and r["ok"] == 6 and r["ft1_stations"] == 3, r
    r = face_guard.guard(NET_FT1, ft1={"ft0"})                                 # ft1 has 2 stations by plan -> merged
    assert r["fail_counts"] == {"merged": 2}, r
    (tmp_path / "ft_stations.txt").write_text("# slot stations in out\nft0 1 S W\nft1 2 S W\n")
    assert face_guard.read_ft1(tmp_path / "ft_stations.txt") == {"ft0"}
    cross = NET_FT1.replace(".QN(ft0_o[1])", ".QN(_x_)").replace(".D(ft0_i[1])", ".D(ft0_i[1])")
    assert face_guard.guard(cross, ft1={"ft0", "ft1"})["verdict"] == "FAIL"


NET_PAIR = r"""
module top(clk, t_d, t_out, t_vd, t_vout);
  input clk; input [1:0] t_d; output [1:0] t_out; input t_vd; output t_vout;
  DFFHQNx1_ASAP7_75t_R \t_out[0]$_DFF_P_  (.CLK(clk), .D(t_d[0]), .QN(t_out[0]));
  DFFHQNx1_ASAP7_75t_R \t_out[1]$_DFF_P_  (.CLK(clk), .D(t_d[1]), .QN(t_out[1]));
  DFFHQNx1_ASAP7_75t_R \t_vout$_DFF_P_  (.CLK(clk), .D(t_vd), .QN(t_vout));
endmodule
"""


def test_declared_core_bus_pair_shares_its_register(tmp_path):
    """gen_core_kit_qc ft1_pairs: `pair I O` lines make bit k of I and bit k of O one register (QC-A0 node TOREG)."""
    (tmp_path / "ft_stations.txt").write_text("# core kit\npair t_d t_out\npair t_vd t_vout\n")
    ft1 = face_guard.read_ft1(tmp_path / "ft_stations.txt")
    assert ft1 == {"t_d>t_out", "t_vd>t_vout"}
    assert face_guard.guard(NET_PAIR)["fail_counts"] == {"merged": 6}            # undeclared: merged
    r = face_guard.guard(NET_PAIR, ft1=ft1)
    assert r["verdict"] == "PASS" and r["ok"] == 6 and r["ft1_stations"] == 3, r
    assert face_guard.guard(NET_PAIR, ft1={"t_d>t_out"})["fail_counts"] == {"merged": 2}
    assert face_guard.guard(NET_PAIR, ft1={"t_out>t_d"})["verdict"] == "FAIL"   # direction is part of the pair
    cross = NET_PAIR.replace(".D(t_d[0]), .QN(t_out[0])", ".D(t_d[1]), .QN(t_out[0])").replace(
        ".D(t_d[1]), .QN(t_out[1])", ".D(t_d[0]), .QN(t_out[1])")
    assert face_guard.guard(cross, ft1=ft1)["verdict"] == "FAIL"                  # bit k must pair with bit k
    assert r["pairs_verified"] == {"t_d>t_out": 2, "t_vd>t_vout": 1}


def _fg_pair(net, ft1=("t_d>t_out", "t_vd>t_vout")):
    return face_guard.guard(net, ft1=set(ft1))


def test_declared_pair_reversed_direction_fails():
    """the declaration names input>output; 'pair t_out t_d' (reversed) exempts nothing and is itself a pair FAIL."""
    r = _fg_pair(NET_PAIR, ft1=("t_out>t_d", "t_vout>t_vd"))
    assert r["verdict"] == "FAIL" and r["fail_counts"]["merged"] == 6 and r["fail_counts"]["pair"] == 2, r


def test_declared_pair_mutant_extra_fanout_fails():
    """MUTANT: the pair flop's output also feeds a second flop (t_out[0] net has another load) -> FAIL."""
    m = NET_PAIR.replace("endmodule", "  DFFHQNx1_ASAP7_75t_R \\x$_DFF_P_  (.CLK(clk), .D(t_out[0]), .QN(xq));\nendmodule")
    m = m.replace("input t_vd; output t_vout;", "input t_vd; output t_vout; wire xq;")
    r = _fg_pair(m)
    assert r["verdict"] == "FAIL" and "shared" in r["fail_counts"] and "pair" in r["fail_counts"], r


def test_declared_pair_mutant_input_fanout_fails():
    """MUTANT: t_d[1] also loads a second flop (input fanout 2) -> FAIL."""
    m = NET_PAIR.replace("endmodule", "  DFFHQNx1_ASAP7_75t_R \\y$_DFF_P_  (.CLK(clk), .D(t_d[1]), .QN(yq));\nendmodule")
    m = m.replace("input t_vd; output t_vout;", "input t_vd; output t_vout; wire yq;")
    r = _fg_pair(m)
    assert r["verdict"] == "FAIL" and "shared" in r["fail_counts"] and "pair" in r["fail_counts"], r


def test_declared_pair_mutant_two_stations_fails():
    """MUTANT: t_d[1] -> flop A -> flop B -> t_out[1] (two stations: +1 cycle).  Each bit then has its own register, so
    the plain face check passes; the declared one-station pair must FAIL."""
    m = NET_PAIR.replace("DFFHQNx1_ASAP7_75t_R \\t_out[1]$_DFF_P_  (.CLK(clk), .D(t_d[1]), .QN(t_out[1]));",
                         "DFFHQNx1_ASAP7_75t_R \\a$_DFF_P_  (.CLK(clk), .D(t_d[1]), .QN(aq));\n"
                         "  DFFHQNx1_ASAP7_75t_R \\b$_DFF_P_  (.CLK(clk), .D(aq), .QN(t_out[1]));")
    m = m.replace("input t_vd; output t_vout;", "input t_vd; output t_vout; wire aq;")
    assert "\\a$_DFF_P_" in m
    assert face_guard.guard(m)["fail_counts"] == {"merged": 4}                  # t_d/t_out[1] not merged any more
    r = _fg_pair(m)
    assert r["verdict"] == "FAIL" and r["fail_counts"] == {"pair": 1}, r
    assert r["pairs_verified"] == {"t_d>t_out": 1, "t_vd>t_vout": 1}


def test_declared_pair_mutant_width_and_missing_port_fail():
    """MUTANT declarations: a pair naming a port that is absent, or buses of different width -> FAIL."""
    r = _fg_pair(NET_PAIR, ft1=("t_d>t_out", "t_vd>t_vout", "t_x>t_out"))
    assert r["verdict"] == "FAIL" and r["fail_counts"] == {"pair": 1}, r
    r = _fg_pair(NET_PAIR, ft1=("t_d>t_out", "t_vd>t_vout", "t_vd>t_out"))
    assert r["verdict"] == "FAIL" and r["fail_counts"] == {"pair": 1}, r


def test_portless_type_passes_with_empty_pin_table():
    net = "module top(clk);\n  input clk;\nendmodule\n"
    assert face_guard.guard(net, pins=[])["verdict"] == "PASS"
    assert face_guard.guard(net)["verdict"] == "FAIL"


def test_early_core_clock_ports_are_not_data_boundaries():
    net = NET_OK.replace("top(clk, a, o);", "top(clk, clk_c0, clk_c4, a, o);")
    net = net.replace("input clk;", "input clk; input clk_c0; input clk_c4;")
    pins = [dict(bus=b, bit=i) for b in ("a", "o") for i in range(2)]
    r = face_guard.guard(net, pins=pins)
    assert r["verdict"] == "PASS" and r["checked"] == 4 and r["ok"] == 4, r


def test_native_scalar_pins_and_global_reset():
    net = r"""module top(clk, rst_n, a, o);
input clk; input rst_n; input a; output o;
wire q; wire nq;
DFFHQNx1_ASAP7_75t_R u_bin_a_q (.CLK(clk), .D(a), .QN(q));
DFFHQNx1_ASAP7_75t_R u_bout_o_q (.CLK(clk), .D(q), .QN(nq));
INVx3_ASAP7_75t_R out_inv (.A(nq), .Y(o));
endmodule
"""
    r = face_guard.guard(net, pins=[dict(bus="a",bit=None),dict(bus="o",bit=None)])
    assert r["verdict"] == "PASS" and r["checked"] == r["planned_bits"] == 2, r


def test_reset_relay_cell_drives_its_output_directly():
    """S81-PLAN2/STFG 10-25: ot_dp_rrelay must not alias its flop through a kept internal wire (ORFS insbuf then hangs a
    dangling BUF on q, so every rst_o_<k> pin register is 'shared'); the wavefront outs are checked, not skipped."""
    import re
    m = re.search(r"\(\*([^*]*)\*\)\s*module ot_dp_rrelay\b(.*?)endmodule", gen_rtl.CELLS, re.S)
    assert m and "keep_hierarchy" in m.group(1) and "keep" in m.group(1).replace("keep_hierarchy", "")
    body = m.group(2)
    assert "output reg q" in body and "assign" not in body and "(* keep *)" not in body
    assert not re.match(face_guard.SKIP_RE, "rst_o_0") and not re.match(face_guard.SKIP_RE, "start_o_1")
    assert re.match(face_guard.SKIP_RE, "arst_n") and re.match(face_guard.SKIP_RE, "start_i")


def test_reset_relay_cell_synth_has_no_dangling_load(tmp_path):
    """yosys + the ORFS assign-removal step (insbuf): rst_o driven by a relay has exactly one load (the port)."""
    if not shutil.which("yosys"):
        pytest.skip("yosys not installed")
    cells = tmp_path / "cells.sv"
    cells.write_text(gen_rtl.CELLS)
    top = tmp_path / "t.sv"
    top.write_text("module t(input wire clk, input wire a, output wire rst_o_0, output wire rst_o_1);\n"
                   "  wire m;\n  ot_dp_rrelay u0(.clk(clk), .d(a), .q(m));\n"
                   "  ot_dp_rrelay u1(.clk(clk), .d(m), .q(rst_o_0));\n"
                   "  ot_dp_rrelay u2(.clk(clk), .d(m), .q(rst_o_1));\nendmodule\n")
    out = tmp_path / "n.v"
    r = subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {cells} {top}; synth -top t; opt_clean -purge; "
                        f"insbuf; write_verilog -noattr {out}"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    n = out.read_text()
    assert "$_BUF_" not in n.split("module ot_dp_rrelay")[1].split("endmodule")[0], n


def _long_boundary_chains():
    lines = ["module top(clk,a,o); input clk; input a; output o; wire q; wire oq;",
             "wire [11:0] i; wire [7:0] b;"]
    for k in range(12):
        src = "a" if k == 0 else f"i[{k-1}]"
        lines.append(f"BUFx1_ASAP7_75t_R ib{k} (.A({src}), .Y(i[{k}]));")
    lines += ["DFFHQNx1_ASAP7_75t_R in_ff (.CLK(clk), .D(i[11]), .QN(q));",
              "DFFHQNx1_ASAP7_75t_R out_ff (.CLK(clk), .D(q), .QN(oq));"]
    for k in range(9):
        src = "oq" if k == 0 else f"b[{k-1}]"
        dst = "o" if k == 8 else f"b[{k}]"
        lines.append(f"INVx1_ASAP7_75t_R ob{k} (.A({src}), .Y({dst}));")
    return "\n".join(lines + ["endmodule"])


def test_recursive_physical_buffer_chains_and_negative_controls():
    """Normal hold repair can exceed three buffers; topology, own FFs and no logic still apply."""
    net = _long_boundary_chains()
    r = face_guard.guard(net)
    assert r["verdict"] == "PASS" and r["ok"] == 2, r
    logic = net.replace("BUFx1_ASAP7_75t_R ib6", "NAND2x1_ASAP7_75t_R ib6")
    assert face_guard.guard(logic)["verdict"] == "FAIL"
    shared = net.replace("endmodule", "BUFx1_ASAP7_75t_R extra (.A(i[7]), .Y(extra_wire)); endmodule")
    assert "shared" in face_guard.guard(shared)["fail_counts"]
    # A directed buffer cycle returns to the input net, with no terminating FF.
    cycle = net.replace(".Y(i[11])", ".Y(a)").replace(".D(i[11])", ".D(unused)")
    r = face_guard.guard(cycle)
    assert r["verdict"] == "FAIL" and any("cycle" in x for x in r["fails"]["unregistered"]), r
    merged = net.replace(".QN(oq)", ".QN(q)")
    assert face_guard.guard(merged)["verdict"] == "FAIL"


NET_CK2 = r"""
module top(clk, clk_coll, a, o);
  input clk; input clk_coll; input [1:0] a; output [1:0] o;
  wire _0_; wire _1_; wire [1:0] q;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[0]$_DFF_P_  (.CLK(clk_coll), .D(a[0]), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[1]$_DFF_P_  (.CLK(clk_coll), .D(a[1]), .QN(q[1]));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[0]$_DFF_P_  (.CLK(clk), .D(q[0]), .QN(_0_));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[1]$_DFF_P_  (.CLK(clk), .D(q[1]), .QN(_1_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));
  INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));
endmodule
"""


# ---- S81-CORE-LAT-R21: declared landing ring (face register per landing slot, gated slots) --------------------------
def _land_net(icg_shared=False, mux=False, two_roots=False, logic_on_gck=False):
    g1 = "g0" if icg_shared else "g1"
    ck1 = "ckb" if two_roots else "ck"
    d1 = "m" if mux else "x"
    extra = "  AND2x2_ASAP7_75t_R u_m (.A(x), .B(e), .Y(m));\n" if mux else ""
    if logic_on_gck:
        extra += "  AND2x2_ASAP7_75t_R u_l (.A(g0), .B(e), .Y(m));\n"
    return f"""
module top(ck, ckb, e, x, o);
  input ck; input ckb; input e; input x; output o;
  wire g0; wire g1; wire q0; wire q1; wire m; wire _0_;
  ICGx1_ASAP7_75t_R u_cg0 (.CLK(ck), .ENA(e), .SE(1'b0), .GCLK(g0));
  ICGx1_ASAP7_75t_R u_cg1 (.CLK({ck1}), .ENA(e), .SE(1'b0), .GCLK(g1));
{extra}  DFFHQNx1_ASAP7_75t_R s0 (.CLK(g0), .D(x), .QN(q0));
  DFFHQNx1_ASAP7_75t_R s1 (.CLK({g1}), .D({d1}), .QN(q1));
  DFFHQNx1_ASAP7_75t_R \\u_bout_o.q$_DFF_P_ (.CLK(ck), .D(q0), .QN(_0_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o));
endmodule
"""


def test_sdc_clock_ports_parse():
    sdc = ("create_clock -name core -period 833 [get_ports clk]\n"
           "create_clock -name clk_coll -period 833.0000 [get_ports clk_coll]\n"
           "create_clock -name vclk -period 833\n")
    assert face_guard.sdc_clock_ports(sdc) == ["clk", "clk_coll"]


def test_extra_sdc_clock_role_is_exempt():
    # without the SDC clock list the extra clock role is a shared (data) input -> FAIL (coll_n 10-27 case)
    assert face_guard.guard(NET_CK2)["verdict"] == "FAIL"
    r = face_guard.guard(NET_CK2, clocks=["clk", "clk_coll"])
    assert r["verdict"] == "PASS", r["fail_counts"]


def test_sdc_clock_port_planned_as_data_is_refused():
    with pytest.raises(ValueError):
        face_guard.guard(NET_CK2, pins=[{"bus": "clk_coll", "bit": 0}], clocks=["clk_coll"])


def test_main_reads_sdc_beside_pins(tmp_path):
    (tmp_path / "net.v").write_text(NET_CK2)
    (tmp_path / "pins.json").write_text("[]")
    (tmp_path / "constraint.sdc").write_text("create_clock -name clk_coll -period 833 [get_ports clk_coll]\n")
    assert face_guard.main([str(tmp_path / "net.v"), "--pins", str(tmp_path / "pins.json"),
                            "--out", str(tmp_path / "fg.json")]) == 0


SKIP_LAND = r"^(ck|ckb|e)$"


def test_land_slot_word_shares_slot_icg():
    net = _land_net().replace("input x;", "input x; input y;").replace("module top(ck, ckb, e, x, o);", "module top(ck, ckb, e, x, y, o);")
    net = net.replace("endmodule", "  DFFHQNx1_ASAP7_75t_R t0 (.CLK(g0), .D(y), .QN());\n  DFFHQNx1_ASAP7_75t_R t1 (.CLK(g1), .D(y), .QN());\nendmodule")
    r = face_guard.guard(net, "top", skip_re=SKIP_LAND, land={"x": 2, "y": 2})
    assert r["verdict"] == "PASS" and r["land_slot_bits"] == 2, r["fails"]


def test_land_slot_pass():
    r = face_guard.guard(_land_net(), "top", skip_re=SKIP_LAND, land={"x": 2})
    assert r["verdict"] == "PASS", r["fails"]
    assert r["land_slot_bits"] == 1


def test_land_slot_undeclared_is_shared():
    r = face_guard.guard(_land_net(), "top", skip_re=SKIP_LAND)
    assert r["verdict"] == "FAIL" and "shared" in r["fail_counts"]


@pytest.mark.parametrize("kw,cls", [(dict(icg_shared=True), "land_slot"), (dict(mux=True), "land_slot"),
                                    (dict(two_roots=True), "land_slot"), (dict(logic_on_gck=True), "land_slot")])
def test_land_slot_negative(kw, cls):
    r = face_guard.guard(_land_net(**kw), "top", skip_re=SKIP_LAND, land={"x": 2})
    assert r["verdict"] == "FAIL" and cls in r["fail_counts"], r


def test_land_slot_wrong_depth():
    r = face_guard.guard(_land_net(), "top", skip_re=SKIP_LAND, land={"x": 4})
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"]


def test_declared_dead_input_needs_no_load_and_a_proof(tmp_path):
    """QK-CORES-5 10-27 (COORD: declare dead only with a proof receipt): core_tx package_abort / por_n class."""
    dropped = NET_OK.replace(".D(a[1])", ".D(q[0])")             # a[1] loads nothing
    assert "dropped" in face_guard.guard(dropped)["fail_counts"]
    r = face_guard.guard(dropped, dead=["a[1]"])
    assert "dropped" not in r.get("fail_counts", {}) and r["dead_declared"] == ["a[1]"], r
    r = face_guard.guard(NET_OK, dead=["a[1]"])                   # a live (registered) bit declared dead -> FAIL
    assert r["fail_counts"].get("dead") == 1 and r["verdict"] == "FAIL"
    r = face_guard.guard(dropped, dead=["a[1]", "o[0]"])          # an output can never be declared dead
    assert r["fail_counts"].get("dead") == 1
    r = face_guard.guard(dropped, dead=["a[1]", "zz[0]"])         # a bit that is not a port
    assert r["fail_counts"].get("dead") == 1
    ok = dict(schema=face_guard.DEAD_SCHEMA, bits=["a[1]"], proof=dict(verdict="PASS", method="yosys equiv", receipt="x"))
    assert face_guard.dead_input_list(ok) == ["a[1]"]
    for bad in (dict(ok, schema="v0"), dict(ok, bits=["a[.*]"]), dict(ok, bits=["a[1]", "a[1]"]), dict(ok, bits=[]),
                dict(ok, proof=dict(verdict="FAIL", method="m", receipt="x")), dict(ok, proof=dict(verdict="PASS"))):
        with pytest.raises(ValueError):
            face_guard.dead_input_list(bad)
    assert face_guard.kit_dead_list(tmp_path) == []
    (tmp_path / "dead_inputs.json").write_text(json.dumps(ok))
    assert face_guard.kit_dead_list(tmp_path) == ["a[1]"]


# ---- hold_mux land_slot form (COORD 10-28 06:30, DIE-HEAD-8 witness + controls): one-to-one slot flop, own-Q hold,
# mutually exclusive write enables, no leak.  Fixtures = the DIE-HEAD-8 negative-control netlists (face_negctl.py).
_X = "_ASAP7_75t_R"


def _mux_tc():
    return [f"DFFHQNx1{_X} tq0 (.CLK(fclk), .D(nt0), .QN(t0n));", f"DFFHQNx1{_X} tq1 (.CLK(fclk), .D(nt1), .QN(t1n));",
            f"INVx1{_X} it0 (.A(t0n), .Y(t0));", f"INVx1{_X} it1 (.A(t1n), .Y(t1));",
            f"BUFx2{_X} bn0 (.A(t0n), .Y(nt0));", f"XNOR2xp5{_X} xn1 (.A(t0), .B(t1n), .Y(nt1));",
            f"NOR2x1{_X} e0 (.A(t0), .B(t1), .Y(w0));", f"AND2x2{_X} e1 (.A(t0), .B(t1n), .Y(w1));",
            f"AND2x2{_X} e2 (.A(t0n), .B(t1), .Y(w2));", f"AND2x2{_X} e3 (.A(t0), .B(t1), .Y(w3));"] + \
           [f"INVx1{_X} ne{k} (.A(w{k}), .Y(nw{k}));" for k in range(4)]


def _mux_slot(k, w=None, nw=None, hold=True, src="d", tag=""):
    w, nw = w or f"w{k}", nw or f"nw{k}"
    s = [f"DFFHQNx1{_X} sf{tag}{k} (.CLK(fclk), .D(sd{tag}{k}), .QN(sq{tag}{k}n));",
         f"INVx1{_X} si{tag}{k} (.A(sq{tag}{k}n), .Y(sq{tag}{k}));"]
    if hold:
        s.append(f"AO22x1{_X} sm{tag}{k} (.A1({src}), .A2({w}), .B1(sq{tag}{k}), .B2({nw}), .Y(sd{tag}{k}));")
    else:
        s.append(f"AND2x2{_X} sm{tag}{k} (.A({src}), .B({w}), .Y(sd{tag}{k}));")
    return s


def _mux_mod(body, extra_ports="", extra_in=""):
    outs = [p.strip() for p in extra_ports.split(",") if p.strip()]
    ins = [p.strip() for p in extra_in.split(",") if p.strip()]
    hdr = ", ".join(["fclk", "d"] + ins + outs)
    return (f"module top({hdr});\n input fclk; input d;\n" + "".join(f" input {p};\n" for p in ins) +
            "".join(f" output {p};\n" for p in outs) + "\n".join(" " + b for b in body) + "\nendmodule\n")


def _mux_slots4(**kw):
    return sum((_mux_slot(k, **kw) for k in range(4)), [])


MUX4 = {"d": {"D": 4, "form": "hold_mux"}}


def _g(net, land=MUX4):
    return face_guard.guard(net, "top", clocks=["fclk"], land=land)


def test_land_mux_positive():
    r = _g(_mux_mod(_mux_tc() + _mux_slots4()))
    assert r["verdict"] == "PASS" and r["land_mux_bits"] == 1 and r["land_mux_depth"] == {"1": 4}, r["fails"]


def test_land_mux_undeclared_and_icg_declared_still_fail():
    net = _mux_mod(_mux_tc() + _mux_slots4())
    assert "shared" in _g(net, land=None)["fail_counts"]          # default unchanged
    assert "land_slot" in _g(net, land={"d": 4})["fail_counts"]    # ICG form does not accept the mux form
    assert "land_slot" in _g(net, land={"d": {"D": 4, "form": "icg"}})["fail_counts"]


@pytest.mark.parametrize("name,body,ports,D", [
    ("nonexclusive", lambda: _mux_tc() + _mux_slot(0) + _mux_slot(1, w="w0", nw="nw0") + _mux_slot(2) + _mux_slot(3), "", 4),
    ("leak_to_flop", lambda: _mux_tc() + _mux_slots4() + [f"XOR2xp5{_X} lx (.A(d), .B(t0), .Y(lk));",
                                                         f"DFFHQNx1{_X} lf (.CLK(fclk), .D(lk), .QN(lkq));"], "", 4),
    ("leak_to_flop_same_count", lambda: _mux_tc() + _mux_slot(0) + _mux_slot(1) + _mux_slot(2) +
        [f"DFFHQNx1{_X} sf3 (.CLK(fclk), .D(sd3), .QN(sq3n));", f"INVx1{_X} si3 (.A(sq3n), .Y(sq3));",
         f"AO22x1{_X} sm3 (.A1(d), .A2(w3), .B1(sq3), .B2(nw3), .Y(sd3));",
         f"DFFHQNx1{_X} lf (.CLK(fclk), .D(sd3), .QN(lkq));"], "", 4),
    ("leak_to_port", lambda: _mux_tc() + _mux_slots4() + [f"BUFx2{_X} lb (.A(d), .Y(dout));"], "dout", 4),
    ("leak_via_slot_logic_to_port", lambda: _mux_tc() + _mux_slot(0) + _mux_slot(1) + _mux_slot(2) + _mux_slot(3) +
        [f"BUFx2{_X} lb (.A(sd3), .Y(dout));"], "dout", 4),
    ("no_hold", lambda: _mux_tc() + _mux_slots4(hold=False), "", 4),
    ("two_loads_one_flop", lambda: _mux_tc() + [f"DFFHQNx1{_X} sf0 (.CLK(fclk), .D(sd0), .QN(sq0n));",
        f"INVx1{_X} si0 (.A(sq0n), .Y(sq0));", f"AO22x1{_X} smA (.A1(d), .A2(w0), .B1(sq0), .B2(nw0), .Y(x0));",
        f"AND2x2{_X} smB (.A(d), .B(x0), .Y(sd0));"], "", 2),
    ("never_written", lambda: _mux_tc() + _mux_slot(0) + _mux_slot(1) + _mux_slot(2) +
        _mux_slot(3, w="CONST0", nw="CONST1"), "", 4),
    ("two_clocks", lambda: _mux_tc() + _mux_slot(0) + _mux_slot(1) + _mux_slot(2) +
        [f"DFFHQNx1{_X} sf3 (.CLK(ck2), .D(sd3), .QN(sq3n));", f"INVx1{_X} si3 (.A(sq3n), .Y(sq3));",
         f"AO22x1{_X} sm3 (.A1(d), .A2(w3), .B1(sq3), .B2(nw3), .Y(sd3));"], "", 4),
    ("wrong_depth", lambda: _mux_tc() + _mux_slots4(), "", 3),
])
def test_land_mux_mutants(name, body, ports, D):
    net = _mux_mod(body(), ports, extra_in="ck2" if name == "two_clocks" else "")
    net = net.replace("(CONST0)", "(1'b0)").replace("(CONST1)", "(1'b1)")
    r = face_guard.guard(net, "top", clocks=["fclk", "ck2"], land={"d": {"D": D, "form": "hold_mux"}})
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], (name, r["fail_counts"], r["fails"])


def test_land_mux_two_bits_one_flop_is_merged_and_landing_bit_enable_refused():
    # bit e writes the slots of d and e (one AO22 per slot keyed on its own enable): legit two-bit word -> PASS
    two = _mux_tc() + _mux_slots4() + sum((_mux_slot(k, src="e", tag="e") for k in range(4)), [])
    land = {"d": {"D": 4, "form": "hold_mux"}, "e": {"D": 4, "form": "hold_mux"}}
    r = face_guard.guard(_mux_mod(two, extra_in="e"), "top", clocks=["fclk"], land=land)
    assert r["verdict"] == "PASS" and r["land_mux_bits"] == 2, r["fails"]
    # enable of d's slot 0 taken from landing bit e -> data-dependent write: refused
    bad = _mux_tc() + [f"AND2x2{_X} ex (.A(w0), .B(e), .Y(we0));", f"INVx1{_X} nex (.A(we0), .Y(nwe0));"] + \
        _mux_slot(0, w="we0", nw="nwe0") + _mux_slot(1) + _mux_slot(2) + _mux_slot(3)
    r = face_guard.guard(_mux_mod(bad, extra_in="e"), "top", clocks=["fclk"], land={"d": {"D": 4, "form": "hold_mux"},
                                                                                     "e": {"D": 2, "form": "hold_mux"}})
    assert r["verdict"] == "FAIL" and any("landing bit" in x for x in r["fails"]["land_slot"]), r["fails"]


def test_land_spec_and_kit_file(tmp_path):
    assert face_guard.land_spec(4) == (4, "icg") and face_guard.land_spec({"D": 4, "form": "hold_mux"}) == (4, "hold_mux")
    for bad in ({"D": 4, "form": "or_any"}, {"D": 4, "form": "hold_mux", "x": 1}):
        with pytest.raises(ValueError):
            face_guard.land_spec(bad)
    (tmp_path / "net.v").write_text(_mux_mod(_mux_tc() + _mux_slots4()))
    (tmp_path / "pins.json").write_text("[]")
    (tmp_path / "constraint.sdc").write_text("create_clock -name fclk -period 833 [get_ports fclk]\n")
    (tmp_path / "land_slots.json").write_text(json.dumps({"buses": MUX4}))
    assert face_guard.main([str(tmp_path / "net.v"), "--pins", str(tmp_path / "pins.json")]) == 0


# ---- forwarded clock output contract (DIE-HEAD-9 FACE (c)): create_generated_clock -source S -divide_by 1 T
def _exp_net(body):
    data = (f" DFFHQNx1{_X} f1 (.CLK(clk), .D(a), .QN(q)); DFFHQNx1{_X} f2 (.CLK(clk), .D(q), .QN(n2));"
            f" INVx1{_X} io (.A(n2), .Y(o));\n")
    return ("module top(clk, clk_t3, a, o, fclk_out_o);\n input clk; input clk_t3; input a; output o; "
            "output fclk_out_o;\n" + data + body + "\nendmodule\n")


def test_sdc_clock_exports_parse():
    sdc = ("create_generated_clock -name fclk_out_o -master_clock clk -source [get_ports clk_t3] -divide_by 1 "
           "[get_ports fclk_out_o]\ncreate_generated_clock -name g2 -source [get_ports clk] -divide_by 2 [get_ports h]\n")
    assert face_guard.sdc_clock_exports(sdc) == [("fclk_out_o", "clk_t3")]


@pytest.mark.parametrize("body,exports,ok", [
    (f" BUFx2{_X} b (.A(clk_t3), .Y(fclk_out_o));", [("fclk_out_o", "clk_t3")], True),
    (f" INVx2{_X} i0 (.A(clk_t3), .Y(n)); INVx2{_X} i1 (.A(n), .Y(fclk_out_o));", [("fclk_out_o", "clk_t3")], True),
    (f" BUFx2{_X} b (.A(clk_t3), .Y(fclk_out_o));", (), False),                       # undeclared: feedthrough
    (f" BUFx2{_X} b (.A(clk), .Y(fclk_out_o));", [("fclk_out_o", "clk_t3")], False),   # wrong source (old RTL)
    (f" INVx2{_X} i0 (.A(clk_t3), .Y(fclk_out_o));", [("fclk_out_o", "clk_t3")], False),  # inverted
    (f" BUFx2{_X} b (.A(clk_t3), .Y(n)); BUFx2{_X} c (.A(n), .Y(fclk_out_o)); BUFx2{_X} l (.A(n), .Y(z));",
     [("fclk_out_o", "clk_t3")], False),                                                # chain net shared
    (f" AND2x2{_X} a (.A(clk_t3), .B(clk), .Y(fclk_out_o));", [("fclk_out_o", "clk_t3")], False),  # logic
])
def test_clock_export_contract(body, exports, ok):
    r = face_guard.guard(_exp_net(body), "top", exports=exports)
    assert (r["verdict"] == "PASS") == ok, r["fails"]
    if ok:
        assert r["clock_exports"] == {"fclk_out_o": "clk_t3"}
    elif exports:
        assert "clock_export" in r["fail_counts"], r["fails"]


# ---- ring_start form (DIE-HEAD-21): the count-aligned ring START input (t_rst_n of ot_meso_ring_ca + p_start of the
# count origin) carries no face flop; its fan-out may end only in the declared ring's writer flops and the origin's
# start sampler flops.  Fixture = hierarchical mini ring (u_cland_d, writes gated by st) + origin_s (u_cland_origin).
def _rs_ring():
    gate = [f"AND2x2{_X} g{k} (.A(w{k}), .B(st), .Y(wg{k}));" for k in range(4)] + \
           [f"INVx1{_X} ng{k} (.A(wg{k}), .Y(nwg{k}));" for k in range(4)]
    tc = [x.replace(".D(nt0)", ".D(ntg0)").replace(".D(nt1)", ".D(ntg1)") for x in _mux_tc()] + \
         [f"AND2x2{_X} tg0 (.A(nt0), .B(st), .Y(ntg0));", f"AND2x2{_X} tg1 (.A(nt1), .B(st), .Y(ntg1));"]
    body = tc + gate + sum((_mux_slot(k, w=f"wg{k}", nw=f"nwg{k}") for k in range(4)), [])
    return "module ot_ring(fclk, d, st);\n input fclk; input d; input st;\n " + "\n ".join(body) + "\nendmodule\n"


def _rs_origin(extra=()):
    body = [f"DFFLQNx1{_X} sf (.CLK(clk), .D(st), .QN(sfn));", f"INVx2{_X} ie (.A(efall), .Y(nef));",
            f"NOR2x1{_X} n0 (.A(sfn), .B(nef), .Y(a1));", f"AND2x4{_X} a0 (.A(st), .B(nef), .Y(a2));",
            f"OA21x2{_X} o0 (.A1(a1), .A2(a2), .B(rq), .Y(s0d));", f"DFFHQNx1{_X} s0 (.CLK(clk), .D(s0d), .QN(s0n));"]
    return ("module ot_origin(clk, st, efall, rq);\n input clk; input st; input efall; input rq;\n " +
            "\n ".join(body + list(extra)) + "\nendmodule\n")


def _rs_net(top_extra=(), outs="", origin_extra=(), extra_in=""):
    o = [p.strip() for p in outs.split(",") if p.strip()]
    xi = [p.strip() for p in extra_in.split(",") if p.strip()]
    hdr = ", ".join(["clk", "fclk", "d", "st", "strap_efall", "rst_n"] + xi + o)
    top = (f"module top({hdr});\n input clk; input fclk; input d; input st; input strap_efall; input rst_n;\n" +
           "".join(f" input {p};\n" for p in xi) + "".join(f" output {p};\n" for p in o) +
           f" DFFHQNx1{_X} rf (.CLK(clk), .D(rst_n), .QN(rq));\n"
           " ot_ring u_cland_d (.fclk(fclk), .d(d), .st(st));\n"
           " ot_origin u_cland_origin (.clk(clk), .st(st), .efall(strap_efall), .rq(rq));\n" +
           "".join(f" {x}\n" for x in top_extra) + "endmodule\n")
    return _rs_ring() + _rs_origin(origin_extra) + top


RS = {"d": {"D": 4, "form": "hold_mux"}, "st": {"form": "ring_start", "ring": "d"}}


def _rs(net, land=RS, straps=("strap_efall",)):
    return face_guard.guard(net, "top", clocks=["fclk"], land=land, straps=list(straps))


def test_ring_start_ring_with_declared_dead_bit():
    # DIE-QC-69 11-04 (QC su_c x_su_l0_p1_i[449]): a declared dead ring bit has no slot, the live bits prove the ring
    net = _rs_net().replace("input d; input st; input strap_efall", "input [1:0] d; input st; input strap_efall") \
        .replace(".d(d)", ".d(d[0])")
    land = RS
    r = face_guard.guard(net, "top", clocks=["fclk"], land=land, straps=["strap_efall"], dead=["d[1]"])
    assert r["verdict"] == "PASS" and r["dead_declared"] == ["d[1]"] and r["ring_start_bits"] == 1, r["fails"]
    r = face_guard.guard(net, "top", clocks=["fclk"], land=land, straps=["strap_efall"])
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"]


def test_ring_start_positive_and_default_unchanged():
    r = _rs(_rs_net())
    assert r["verdict"] == "PASS" and r["ring_start_bits"] == 1 and r["land_mux_bits"] == 1, r["fails"]
    rec = r["ring_start"]["st"]
    assert rec["writer_flops"] == 6 and rec["ring"] == ["d"]                 # 2 write-count + 4 slot flops
    assert rec["sampler_flops"] == ["u_cland_origin/s0", "u_cland_origin/sf"]
    assert "shared" in _rs(_rs_net(), land={"d": RS["d"]})["fail_counts"]     # undeclared start: today's FAIL


@pytest.mark.parametrize("name,kw,land", [
    ("leak_to_other_flop", dict(top_extra=[f"BUFx2{_X} lb (.A(st), .Y(stb));",
                                           f"DFFHQNx1{_X} lf (.CLK(clk), .D(stb), .QN(lq));"]), RS),
    ("leak_to_fclk_flop_outside_ring", dict(top_extra=[f"DFFHQNx1{_X} lf (.CLK(fclk), .D(st), .QN(lq));"]), RS),
    ("leak_to_port", dict(top_extra=[f"BUFx2{_X} lb (.A(st), .Y(so));"], outs="so"), RS),
    ("leak_to_clock_pin", dict(top_extra=[f"DFFHQNx1{_X} lf (.CLK(st), .D(rst_n), .QN(lq));"]), RS),
    ("third_origin_flop", dict(origin_extra=[f"DFFHQNx1{_X} s9 (.CLK(clk), .D(st), .QN(s9n));"]), RS),
    ("origin_cone_data_port", dict(extra_in="xd"), RS),     # sampler D gated by a data port (not a strap)
    ("undeclared_ring", {}, {"d": RS["d"], "st": {"form": "ring_start", "ring": "zz"}}),
    ("ring_not_hold_mux", {}, {"d": 4, "st": {"form": "ring_start", "ring": "d"}}),
])
def test_ring_start_mutants(name, kw, land):
    net = _rs_net(**kw)
    if name == "origin_cone_data_port":
        net = net.replace(".rq(rq));", ".rq(xd));")
    r = _rs(net, land=land)
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], (name, r["fail_counts"], r["fails"])
    assert any(x.startswith("st:") for x in r["fails"]["land_slot"]), (name, r["fails"])


def test_ring_start_spec():
    assert face_guard.land_spec({"form": "ring_start", "ring": "i"}) == (0, "ring_start")
    assert face_guard.ring_spec({"form": "ring_start", "ring": ["i", "j"]}) == ["i", "j"]
    for bad in ({"form": "ring_start"}, {"form": "ring_start", "ring": "i", "D": 4}, {"form": "ring_start", "ring": []},
                {"form": "ring_start", "ring": ["i", "i"]}, {"form": "ring_start", "ring": 3}):
        with pytest.raises(ValueError):
            face_guard.land_spec(bad)
def test_halfadder_outputs_follow_asap7_liberty():
    # SIMPLE RVT TT HAxp5: CON=(!A)+(!B), SN=(A*B)+(!A*!B).
    for a in (False, True):
        for b in (False, True):
            assert face_guard.cell_fn("HAxp5_ASAP7_75t_R", {"A": a, "B": b}, "CON") == (not (a and b))
            assert face_guard.cell_fn("HAxp5_ASAP7_75t_R", {"A": a, "B": b}, "SN") == (a == b)
    import pytest
    with pytest.raises(KeyError):
        face_guard.cell_fn("HAxp5_ASAP7_75t_R", {"A": True, "B": False}, "Y")


def test_land_mux_halfadder_count_decode_and_bad_output_control():
    # Replace binary-count slot-0 NOR with HA.CON then invert: A&B is
    # slot-3's enable.  Replacing slot-3 AND preserves exactly the same net.
    body = _mux_tc() + _mux_slots4()
    old = f"AND2x2{_X} e3 (.A(t0), .B(t1), .Y(w3));"
    assert old in body
    body[body.index(old)] = (f"HAxp5{_X} e3 (.A(t0), .B(t1), .CON(hcon), .SN(hsum));\n"
                             f"INVx1{_X} hi (.A(hcon), .Y(w3));")
    assert _g(_mux_mod(body))["verdict"] == "PASS"
    bad = [x.replace(".A(hcon)", ".A(hsum)") for x in body]
    assert _g(_mux_mod(bad))["verdict"] == "FAIL"


def _rs_status_helper(clock='fclk', module='ot_meso_ca_status_copy'):
    text = _rs_net()
    helper = (f'module {module}(clk, st); input clk; input st; '
              f'DFFHQNx1{_X} status_ff (.CLK(clk), .D(st), .QN(q)); endmodule\n')
    text = text.replace('module ot_ring(fclk, d, st);',
                        'module ot_ring(fclk, d, st);')
    a = text.index('module ot_ring('); b = text.index('endmodule', a)
    text = text[:b] + f'{module} \\g_control_status_copy.u_guard_status (.clk({clock}), .st(st));\n' + text[b:]
    return helper + text


def test_ring_start_typed_status_helper_and_wrong_clock():
    r = _rs(_rs_status_helper())
    assert r['verdict'] == 'PASS', r['fails']
    assert r['ring_start']['st']['writer_flops'] == 7
    # The same helper on a different clock is not a ring writer, and the same
    # instance name with an unrelated module type grants no permission.
    for text in (_rs_status_helper('d'), _rs_status_helper(module='unrelated_status')):
        r = _rs(text)
        assert r['verdict'] == 'FAIL' and 'land_slot' in r['fail_counts'], r['fails']


def _origin_only_net():
    text = _rs_net().replace('ot_origin', 'ot_dp_landing_origin_s')
    text = text.replace('.d(d), .st(st));', '.d(d), .st(rst_n));')
    return text


def test_explicit_typed_origin_start_and_mutants():
    spec = dict(RS, st={'form':'origin_start', 'origin':'u_cland_origin'})
    r = _rs(_origin_only_net(), land=spec)
    assert r['verdict'] == 'PASS', r['fails']
    assert r['ring_start']['st']['writer_flops'] == 0
    assert len(r['ring_start']['st']['sampler_flops']) == 2
    for text, land in [(_origin_only_net(), RS),
                       (_origin_only_net().replace('ot_dp_landing_origin_s', 'unrelated_origin'), spec),
                       (_origin_only_net().replace('sf (.CLK(clk)', 'sf (.CLK(fclk)'), spec),
                       (_origin_only_net().replace('.rq(rq));', '.rq(d));'), spec),
                       (_origin_only_net(), dict(RS, st={'form':'origin_start','origin':'wrong_origin'}))]:
        r = _rs(text, land=land)
        assert r['verdict'] == 'FAIL' and 'land_slot' in r['fail_counts'], r['fails']



def test_typed_regional_origin_preserves_sampler_guards():
    # Regional outputs add downstream state, while original SF/S0 remain the
    # only two samplers of the external START pin (proved regional mechanism).
    spec = dict(RS, st={'form':'origin_start', 'origin':'u_cland_origin'})
    text = _origin_only_net().replace('ot_dp_landing_origin_s', 'ot_dp_landing_origin_s_regional')
    good = _rs(text, land=spec)
    assert good['verdict'] == 'PASS', good['fails']
    assert len(good['ring_start']['st']['sampler_flops']) == 2
    for mutant in (text.replace('sf (.CLK(clk)', 'sf (.CLK(fclk)'),
                   text.replace('ot_dp_landing_origin_s_regional', 'unrelated_regional_origin')):
        bad = _rs(mutant, land=spec)
        assert bad['verdict'] == 'FAIL' and 'land_slot' in bad['fail_counts'], bad['fails']


def _flat_like_odb(text, top="top"):
    """Emit the hierarchical test netlist as ONE flat module with the same hierarchical instance paths (what an
    ODB write_verilog of the synthesized design looks like): module types are lost, paths kept."""
    mods = face_guard.parse(text)
    T = mods[top]
    F = face_guard.Flat(mods, top)
    names, n = {}, [0]

    def w(b):
        if b.startswith("CONST_"):
            return "1'b1" if b.endswith("1") else "1'b0"
        r = F.find(b)
        if r not in names:
            names[r] = f"\\n_{n[0]} "
            n[0] += 1
        return names[r]
    body = []
    for m, path, pp in F.cells:
        conns = ", ".join(f".{p}({w(bits[0])})" for p, (d, bits) in pp.items() if bits)
        body.append(f" {m} \\{path} ({conns});")
    ports = [p for p in T.ports]
    decl = "".join(f" {T.dirs[p]} {p};\n" for p in ports)
    asg = "".join(f" assign {w(p)} = {p};\n" for p in ports)
    wires = "".join(f" wire {v};\n" for v in names.values())
    return f"module {top}({', '.join(ports)});\n{decl}{wires}{asg}" + "\n".join(body) + "\nendmodule\n"


def test_flat_odb_netlist_types_from_hierarchical_netlist():
    # ODB-written netlists are flat: typed status-copy / origin proofs need the hierarchical netlist's types.
    hier = _rs_status_helper()
    flat = _flat_like_odb(hier)
    assert len(face_guard.parse(flat)) == 1
    assert _rs(hier)["verdict"] == "PASS"
    r = _rs(flat)
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], r["fails"]     # no types: fail-closed
    ok = face_guard.guard(flat, "top", clocks=["fclk"], land=RS, straps=["strap_efall"],
                          types=face_guard.hier_module_types(hier, "top"))
    assert ok["verdict"] == "PASS", ok["fails"]
    bad = face_guard.hier_module_types(_rs_status_helper(module="unrelated_status"), "top")
    r = face_guard.guard(flat, "top", clocks=["fclk"], land=RS, straps=["strap_efall"], types=bad)
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], r["fails"]
    with pytest.raises(ValueError):
        face_guard.guard(flat, "top", clocks=["fclk"], land=RS, straps=["strap_efall"], types=("other", {}))
    # typed origin_start on the flat netlist
    spec = dict(RS, st={"form": "origin_start", "origin": "u_cland_origin"})
    oh = _origin_only_net()
    of = _flat_like_odb(oh)
    assert _rs(of, land=spec)["verdict"] == "FAIL"
    r = face_guard.guard(of, "top", clocks=["fclk"], land=spec, straps=["strap_efall"],
                         types=face_guard.hier_module_types(oh, "top"))
    assert r["verdict"] == "PASS", r["fails"]
    bad = face_guard.hier_module_types(oh.replace("ot_dp_landing_origin_s", "unrelated_origin"), "top")
    r = face_guard.guard(of, "top", clocks=["fclk"], land=spec, straps=["strap_efall"], types=bad)
    assert r["verdict"] == "FAIL", r["fails"]


def test_run_kit_odb_face_guard_reads_hierarchical_types():
    import gen_phys
    assert "1_synth_odb.v --types-from \\$N" in gen_phys.RUN_KIT


# Relaycat START uses the existing single reset-qualified source sampler,
# declared with the same origin_start role. Hardware-cone proof is unchanged.
def _relay_start_net(extra="", gate="AND2x2", typ="ot_dp_landing_relay"):
    text = _origin_only_net()
    a = text.index("module ot_dp_landing_origin_s(")
    b = text.index("endmodule", a) + len("endmodule")
    body = (f"module {typ}(clk, st, efall, rq); input clk, st, efall, rq; "
            f"{gate}{_X} rg (.A(st), .B(rq), .Y(sd)); "
            f"DFFHQNx1{_X} sf (.CLK(clk), .D(sd), .QN(q)); {extra} endmodule")
    return (text[:a] + body + text[b:]).replace("ot_dp_landing_origin_s u_cland_origin", f"{typ} u_cland_origin")


def test_explicit_typed_relay_start_and_hardware_mutants():
    spec = dict(RS, st={"form": "origin_start", "origin": "u_cland_origin"})
    text = _relay_start_net()
    r = _rs(text, land=spec)
    assert r["verdict"] == "PASS", r["fails"]
    assert r["ring_start"]["st"]["sampler_flops"] == ["u_cland_origin/sf"]
    for bad, slots in [
        (text, RS),
        (_relay_start_net(typ="unrelated_relay"), spec),
        (_relay_start_net(gate="XOR2x2"), spec),
        (text.replace(".B(rq)", ".B(q)"), spec),
        (_relay_start_net(extra=f"DFFHQNx1{_X} sf2 (.CLK(clk), .D(st), .QN(q2));"), spec),
        (text.replace(".B(rq)", ".B(efall)"), dict(spec)),
        (text.replace("sf (.CLK(clk)", "sf (.CLK(st)"), spec),
    ]:
        # efall becomes a DATA port (no strap declaration): must not qualify.
        straps = () if ".B(efall)" in bad else ("strap_efall",)
        got = _rs(bad, land=slots, straps=straps)
        assert got["verdict"] == "FAIL", got


def test_flat_relay_requires_actual_original_module_type():
    text = _relay_start_net()
    spec = dict(RS, st={"form": "origin_start", "origin": "u_cland_origin"})
    flat = _flat_like_odb(text)
    assert _rs(flat, land=spec)["verdict"] == "FAIL"
    got = face_guard.guard(flat, "top", clocks=["fclk"], land=spec, straps=["strap_efall"],
                           types=face_guard.hier_module_types(text, "top"))
    assert got["verdict"] == "PASS", got["fails"]


def _relay_copy_vehicle():
    relay = f"""module ot_dp_landing_relay(clk, st, rq, q);
input clk; input st; input rq; output q;
AND2x2{_X} gate (.A(st), .B(rq), .Y(d));
DFFHQNx1{_X} ff (.CLK(clk), .D(d), .QN(nq));
INVx1{_X} out_inv (.A(nq), .Y(q));
endmodule
"""
    top = f"""module top(clk, rst_n, st, mission, o0, o1);
input clk; input rst_n; input st; output mission; output o0; output o1;
DFFHQNx1{_X} reset_ff (.CLK(clk), .D(rst_n), .QN(rq));
ot_dp_landing_relay origin (.clk(clk), .st(st), .rq(rq), .q(mission));
ot_dp_landing_relay copy0 (.clk(clk), .st(st), .rq(rq), .q(o0));
ot_dp_landing_relay copy1 (.clk(clk), .st(st), .rq(rq), .q(o1));
endmodule
"""
    spec = {"st": {"form": "origin_start", "origin": "origin", "copies": ["copy0", "copy1"]}}
    return relay + top, spec


def test_declared_relay_copies_are_same_state_private_face_registers():
    text, spec = _relay_copy_vehicle()
    got = face_guard.guard(text, "top", land=spec)
    assert got["verdict"] == "PASS", got["fails"]
    assert got["ring_start"]["st"]["face_copies"] == {"copy0": "o0", "copy1": "o1"}
    # No declared copy can be omitted or added silently.
    for copies in (["copy0"], ["copy0", "copy1", "wrong"]):
        bad = {"st": dict(spec["st"], copies=copies)}
        assert face_guard.guard(text, "top", land=bad)["verdict"] == "FAIL"


@pytest.mark.parametrize("mutant", ["wrong_type", "wrong_reset", "inverted_reset", "wrong_data", "wrong_clock",
                                    "shared_output", "two_outputs", "extra_ff", "extra_cycle"])
def test_declared_relay_copy_mutants_fail_closed(mutant):
    text, spec = _relay_copy_vehicle()
    if mutant == "wrong_type":
        other = text[:text.index("module top")].replace("module ot_dp_landing_relay", "module unrelated_relay")
        text = other + text.replace("ot_dp_landing_relay copy0", "unrelated_relay copy0")
    elif mutant == "wrong_reset":
        text = text.replace("copy0 (.clk(clk), .st(st), .rq(rq)", "copy0 (.clk(clk), .st(st), .rq(1'b1)")
    elif mutant == "inverted_reset":
        text = text.replace("ot_dp_landing_relay copy0", f"INVx1{_X} ir (.A(rq), .Y(nrq)); ot_dp_landing_relay copy0")
        text = text.replace("copy0 (.clk(clk), .st(st), .rq(rq)", "copy0 (.clk(clk), .st(st), .rq(nrq)")
    elif mutant == "wrong_data":
        text = text.replace("copy0 (.clk(clk), .st(st)", "copy0 (.clk(clk), .st(rq)")
    elif mutant == "wrong_clock":
        text = text.replace("copy0 (.clk(clk)", "copy0 (.clk(st)")
    elif mutant == "shared_output":
        text = text.replace(".q(o0));", ".q(o0)); " + f"DFFHQNx1{_X} leak (.CLK(clk), .D(o0), .QN(lq));")
    elif mutant == "two_outputs":
        text = text.replace(".q(o1));", ".q(o0)); assign o1 = o0;")
    elif mutant == "extra_ff":
        text = text.replace("INVx1" + _X + " out_inv", f"DFFHQNx1{_X} extra (.CLK(clk), .D(st), .QN(extra_q)); INVx1{_X} out_inv")
    else:
        text = text.replace("copy0 (.clk(clk), .st(st)", "copy0 (.clk(clk), .st(mission)")
    got = face_guard.guard(text, "top", land=spec)
    assert got["verdict"] == "FAIL", (mutant, got)


def _unloaded_origin_vehicle():
    """DIE-QC-59 11-01 (QC slw_hc3): the relay partition's own start is unused, synthesis removed the origin flop."""
    text, spec = _relay_copy_vehicle()
    text = text.replace("module top(clk, rst_n, st, mission, o0, o1);", "module top(clk, rst_n, st, o0, o1);")
    text = text.replace("input clk; input rst_n; input st; output mission;", "input clk; input rst_n; input st;")
    text = text.replace("ot_dp_landing_relay origin (.clk(clk), .st(st), .rq(rq), .q(mission));\n", "")
    return text, spec


def test_unloaded_removed_origin_keeps_copy_proofs():
    text, spec = _unloaded_origin_vehicle()
    got = face_guard.guard(text, "top", land=spec)
    assert got["verdict"] == "PASS", got["fails"]
    rec = got["ring_start"]["st"]
    assert rec["face_copies"] == {"copy0": "o0", "copy1": "o1"} and rec["origin_removed_unloaded"] == "origin"
    # still fail-closed: an undeclared copy, a missing copy, a wrong-type or wrong-data copy
    for copies in (["copy0"], ["copy0", "copy1", "wrong"]):
        assert face_guard.guard(text, "top", land={"st": dict(spec["st"], copies=copies)})["verdict"] == "FAIL"
    for a, b in (("copy1 (.clk(clk), .st(st)", "copy1 (.clk(clk), .st(rq)"), (".q(o1));", ".q(o0)); assign o1 = o0;")):
        assert face_guard.guard(text.replace(a, b), "top", land=spec)["verdict"] == "FAIL", a
    other = text[:text.index("module top")].replace("module ot_dp_landing_relay", "module unrelated_relay")
    bad = other + text.replace("ot_dp_landing_relay copy0", "unrelated_relay copy0")
    assert face_guard.guard(bad, "top", land=spec)["verdict"] == "FAIL"


def _writer_stage_vehicle():
    """QC W1 on a relay type: stage0 samples the origin's input on its own raw reset and feeds the far FSTART relay."""
    text, spec = _relay_copy_vehicle()
    text = text.replace("module top(clk, rst_n, st, mission, o0, o1);", "module top(clk, rst_n, st, mission, o0, o1, o2);")
    text = text.replace("output o1;\n", "output o1; output o2;\n")
    text = text.replace("endmodule\n", "@@", 1).replace("endmodule\n", f"""DFFHQNx1{_X} reset_far (.CLK(clk), .D(rq), .QN(rq2));
ot_dp_landing_relay stage0 (.clk(clk), .st(st), .rq(rq2), .q(s0));
ot_dp_landing_relay far (.clk(clk), .st(s0), .rq(rq), .q(o2));
endmodule
""").replace("@@", "endmodule\n")
    return text, {"st": dict(spec["st"], stages=["stage0"])}


def test_writer_stage_is_own_kind_not_a_copy():
    text, spec = _writer_stage_vehicle()
    got = face_guard.guard(text, "top", land=spec)
    assert got["verdict"] == "PASS", got["fails"]
    rec = got["ring_start"]["st"]
    assert rec["writer_stages"] == {"stage0": "far"} and rec["face_copies"] == {"copy0": "o0", "copy1": "o1"}
    # the same flop declared as a copy keeps the old full proof, and an undeclared stage is an extra sampler
    as_copy = {"st": dict(spec["st"], copies=["copy0", "copy1", "stage0"])}
    as_copy["st"].pop("stages")
    assert face_guard.guard(text, "top", land=as_copy)["verdict"] == "FAIL"
    undeclared = {"st": {k: v for k, v in spec["st"].items() if k != "stages"}}
    assert face_guard.guard(text, "top", land=undeclared)["verdict"] == "FAIL"


@pytest.mark.parametrize("a,b", [
    ("stage0 (.clk(clk), .st(st), .rq(rq2), .q(s0));", f"stage0 (.clk(clk), .st(st), .rq(1'b1), .q(s0));"),
    ("stage0 (.clk(clk), .st(st)", "stage0 (.clk(clk), .st(rq)"),
    ("stage0 (.clk(clk)", "stage0 (.clk(st)"),
    ("far (.clk(clk), .st(s0), .rq(rq), .q(o2));", f"far (.clk(clk), .st(s0), .rq(rq), .q(o2)); DFFHQNx1{_X} leak (.CLK(clk), .D(s0), .QN(lq));"),
    ("far (.clk(clk), .st(s0), .rq(rq), .q(o2));", "far (.clk(clk), .st(rq), .rq(rq), .q(o2)); assign o2 = s0;"),
])
def test_writer_stage_mutants_fail_closed(a, b):
    text, spec = _writer_stage_vehicle()
    assert a in text
    assert face_guard.guard(text.replace(a, b), "top", land=spec)["verdict"] == "FAIL", a


def test_writer_stage_wrong_next_type_fails_closed():
    text, spec = _writer_stage_vehicle()
    other = text[:text.index("module top")].replace("module ot_dp_landing_relay", "module unrelated_relay")
    bad = other + text.replace("ot_dp_landing_relay far", "unrelated_relay far")
    assert face_guard.guard(bad, "top", land=spec)["verdict"] == "FAIL"


def test_origin_stage_spec_refuses_ambiguous_declarations():
    for st in ([], ["origin"], ["copy0"], ["a", "a"], "stage0"):
        with pytest.raises(ValueError):
            face_guard.origin_spec({"form": "origin_start", "origin": "origin", "copies": ["copy0"], "stages": st})


def test_present_but_unreached_origin_still_fails():
    text, spec = _relay_copy_vehicle()
    text = text.replace("origin (.clk(clk), .st(st)", "origin (.clk(clk), .st(rst_n)")
    assert face_guard.guard(text, "top", land=spec)["verdict"] == "FAIL"


def test_origin_copy_spec_refuses_ambiguous_declarations():
    for copies in ([], "copy", ["copy", "copy"], ["origin"], [""], [1]):
        with pytest.raises(ValueError):
            face_guard.origin_spec({"form": "origin_start", "origin": "origin", "copies": copies})


def _registered_onehot_vehicle(mutant=None):
    body = [f"DFFHQNx1{_X} reset_ff (.CLK(fclk), .D(rst_n), .QN(nrq));",
            f"INVx1{_X} reset_inv (.A(nrq), .Y(rq));"]
    for k in range(4):
        ck = "rst_n" if mutant == "clock" and k == 1 else "fclk"
        body += [f"DFFHQNx1{_X} wr{k} (.CLK({ck}), .D(wd{k}), .QN(nw{k}));",
                 f"INVx1{_X} wi{k} (.A(nw{k}), .Y(w{k}));"]
        prev = 0 if mutant == "rotation" and k == 2 else (k - 1) % 4
        body.append(f"AND2x2{_X} wd_gate{k} (.A(rq), .B(w{prev}), .Y(normal{k}));")
        if k == 0 or mutant == "two_reset_bits" and k == 1:
            body.append(f"OR2x2{_X} wd_or{k} (.A(normal{k}), .B(nrq), .Y(wd{k}));")
        else:
            body.append(f"BUFx2{_X} wd_buf{k} (.A(normal{k}), .Y(wd{k}));")
    if mutant == "no_reset":
        body = [line.replace(".B(nrq)", ".B(1'b0)") for line in body]
    body += _mux_slots4()
    module = "unrelated_controller" if mutant == "type" else "ot_pl_land_local_kw"
    text = (f"module {module}(fclk, rst_n, d); input fclk; input rst_n; input d;\n" +
            "\n".join(body) + "\nendmodule\n" +
            f"module top(fclk, rst_n, d); input fclk; input rst_n; input d;\n"
            f"{module} local (.fclk(fclk), .rst_n(rst_n), .d(d)); endmodule\n")
    if mutant == "reset_input":
        text = text.replace("rst_n", "enable")
    return text


def test_registered_onehot_requires_mapped_reset_and_full_rotation_proof():
    r = face_guard.guard(_registered_onehot_vehicle(), "top", clocks=["fclk"], land=MUX4)
    assert r["verdict"] == "PASS", r["fails"]
    assert r["registered_onehot"]["local"]["cycle"] == 4
    assert r["registered_onehot"]["local"]["reset_asserted_edges_required"] == 2


@pytest.mark.parametrize("mutant", ["two_reset_bits", "no_reset", "rotation", "clock", "type", "reset_input"])
def test_registered_onehot_mutants_fail_closed(mutant):
    r = face_guard.guard(_registered_onehot_vehicle(mutant), "top", clocks=["fclk"], land=MUX4)
    assert r["verdict"] == "FAIL", (mutant, r)
    assert not r.get("registered_onehot"), (mutant, r)


def test_registered_onehot_needs_declared_reset_role_not_only_reset_name():
    text = _registered_onehot_vehicle()
    r = face_guard.guard(text, "top", skip_re=r"^fclk$", land=MUX4)
    assert r["verdict"] == "FAIL" and not r.get("registered_onehot")


def test_registered_onehot_rejects_unmodeled_sequential_polarity_or_edge():
    text = _registered_onehot_vehicle().replace("DFFHQNx1" + _X + " wr1", "DFFLQNx1" + _X + " wr1")
    r = face_guard.guard(text, "top", clocks=["fclk"], land=MUX4)
    assert r["verdict"] == "FAIL" and not r.get("registered_onehot")


WREG4 = {"d": {"D": 4, "form": "hold_mux"}, "start": {"form": "ring_start", "ring": "d"}}


def _wreg_vehicle(mutant=None, buffered=False):
    """WREG-1 (ot_dp_clk_landing_ca g_wreg): kept per-slot write-enable flops, D = start && slot_nx == k,
    slot_nx = fs_q ? tc + 1 : 0."""
    ff = f"DFFHQNx{'2' if buffered else '1'}{_X}"
    st = "start_b" if buffered else "start"
    wen = (f"module ot_meso_wen_ff(clk, d, q); input clk; input d; output q;\n"
           f" {ff} ff (.CLK(clk), .D(d), .QN(qn));\n INVx1{_X} qi (.A(qn), .Y(q));\nendmodule\n")
    body = [f"DFFHQNx1{_X} fs (.CLK(fclk), .D({st}), .QN(fsn));", f"INVx1{_X} fi (.A(fsn), .Y(fsq));",
            f"DFFHQNx1{_X} tq0 (.CLK(fclk), .D(nx0), .QN(t0n));", f"DFFHQNx1{_X} tq1 (.CLK(fclk), .D(nx1), .QN(t1n));",
            f"INVx1{_X} it0 (.A(t0n), .Y(t0));",
            f"AND2x2{_X} n0 (.A(fsq), .B(t0n), .Y(nx0));",
            f"XNOR2xp5{_X} x1 (.A(t0), .B(t1n), .Y(xt1));", f"AND2x2{_X} n1 (.A(fsq), .B(xt1), .Y(nx1));",
            f"INVx1{_X} nn0 (.A(nx0), .Y(z0));", f"INVx1{_X} nn1 (.A(nx1), .Y(z1));"]
    if buffered:
        body.append(f"BUFx2{_X} sb (.A(start), .Y(start_b));")
    dec = {0: ("z1", "z0"), 1: ("z1", "nx0"), 2: ("nx1", "z0"), 3: ("nx1", "nx0")}
    if mutant == "overlap":
        dec[1] = ("z1", "z1")                 # slot_nx[0] dropped: wen 0 and 1 both set on slot_nx == 0
    ports, decl = "", ""
    for k in range(4):
        hi, lo = dec[k]
        if mutant == "no_reset" and k == 2:
            body.append(f"AND2x2{_X} wg{k} (.A({hi}), .B({lo}), .Y(wd{k}));")
        elif mutant == "stuck" and k == 3:
            body.append(f"TIELOx1{_X} wg{k} (.L(wd{k}));")
        else:
            body.append(f"AND3x1{_X} wg{k} (.A({st}), .B({hi}), .C({lo}), .Y(wd{k}));")
        ck = "fclk2" if mutant == "other_clock" and k == 1 else "fclk"
        d = f"wd{k}"
        if buffered:
            body.append(f"BUFx2{_X} wb{k} (.A(wd{k}), .Y(wdb{k}));")
            d = f"wdb{k}"
        if mutant == "data_leaf" and k == 0:
            body.append(f"AND2x2{_X} wx (.A({d}), .B(e), .Y(wde));")
            d = "wde"
            ports, decl = ", e", " input e;"
        if mutant == "other_clock_leaf" and k == 0:
            body += [f"DFFHQNx1{_X} xf (.CLK(fclk2), .D(fsq), .QN(xn));", f"AND2x2{_X} wx (.A({d}), .B(xn), .Y(wde));"]
            d = "wde"
        if mutant == "wide" and k == 0:
            for j in range(12):
                body += [f"DFFHQNx1{_X} wf{j} (.CLK(fclk), .D(fsq), .QN(wn{j}));",
                         f"AND2x2{_X} wa{j} (.A({d}), .B(wn{j}), .Y(wc{j}));"]
                d = f"wc{j}"
        if mutant == "polarity" and k == 1:
            body += [f"DFFLQNx1{_X} u_wen{k} (.CLK({ck}), .D({d}), .QN(wq{k}));", f"INVx1{_X} wi{k} (.A(wq{k}), .Y(w{k}));"]
        else:
            body.append(f"ot_meso_wen_ff u_wen{k} (.clk({ck}), .d({d}), .q(w{k}));")
        w = f"w{k}"
        if buffered:                          # one wen flop drives its slots through a repeater, as resizing inserts
            body.append(f"BUFx4{_X} wr{k} (.A(w{k}), .Y(wbf{k}));")
            w = f"wbf{k}"
        body.append(f"INVx1{_X} wn_{k} (.A({w}), .Y(nw{k}));")
        if mutant == "inverted_write":        # at-most-one state, but every idle slot writes: a real write conflict
            body += _mux_slot(k, w=f"nw{k}", nw=w)
        else:
            body += _mux_slot(k, w=w, nw=f"nw{k}")
    if mutant == "start_sink":
        body.append(f"DFFHQNx1{_X} sink (.CLK(fclk2), .D(start), .QN(sinkq));")
    return (wen + f"module top(fclk, fclk2, start, d{ports}); input fclk; input fclk2; input start; input d;{decl}\n"
            + "\n".join(" " + b for b in body) + "\nendmodule\n")


def _wreg_guard(text, land=WREG4):
    return face_guard.guard(text, "top", clocks=["fclk", "fclk2"], land=land)


def test_wreg_write_enable_flops_prove_at_most_one_on_falling_edge():
    """DIE-QC-70 WFALL + WREG: writer and write-enable flops all DFFLQN on the raw fclk (ot_meso_wen_ff NEG=1)."""
    r = _wreg_guard(_wreg_vehicle().replace("DFFHQNx", "DFFLQNx"))
    assert r["verdict"] == "PASS", r["fails"]
    (proof,) = r["registered_atmost_one"].values()
    assert proof["flops"] == [f"u_wen{k}/ff" for k in range(4)]


@pytest.mark.parametrize("buffered", [False, True])
def test_wreg_write_enable_flops_prove_at_most_one(buffered):
    r = _wreg_guard(_wreg_vehicle(buffered=buffered))
    assert r["verdict"] == "PASS", r["fails"]
    assert not r.get("registered_onehot")
    (proof,) = r["registered_atmost_one"].values()
    assert proof["flops"] == [f"u_wen{k}/ff" for k in range(4)]
    assert proof["start"] == "start" and proof["start_chain_edges"] == 0
    # the wen flops are ring writers of the start, no origin sampler
    assert r["ring_start"]["start"]["writer_flops"] == 5 and not r["ring_start"]["start"].get("sampler_flops")


@pytest.mark.parametrize("mutant", ["overlap", "no_reset", "stuck", "other_clock", "other_clock_leaf", "data_leaf",
                                    "wide", "polarity", "inverted_write", "start_sink"])
def test_wreg_write_enable_mutants_fail_closed(mutant):
    r = _wreg_guard(_wreg_vehicle(mutant))
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], (mutant, r)
    if mutant not in ("inverted_write", "start_sink"):
        assert not r.get("registered_atmost_one"), (mutant, r)


def test_wreg_start_needs_a_declared_role():
    land = {"d": {"D": 4, "form": "hold_mux"}}
    r = _wreg_guard(_wreg_vehicle(), land=land)
    assert r["verdict"] == "FAIL" and not r.get("registered_atmost_one")


NET_SPARE = r"""
module top(clk, a, o, s);
  input clk; input [1:0] a; output [1:0] o; output [1:0] s;
  wire _0_; wire _1_; wire [1:0] q; wire z; wire g;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[0]$_DFF_P_  (.CLK(clk), .D(a[0]), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[1]$_DFF_P_  (.CLK(clk), .D(a[1]), .QN(q[1]));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[0]$_DFF_P_  (.CLK(clk), .D(q[0]), .QN(_0_));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[1]$_DFF_P_  (.CLK(clk), .D(q[1]), .QN(_1_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));
  INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));
  TIELOx1_ASAP7_75t_R _4_ (.L(z));
  AND2x2_ASAP7_75t_R _5_ (.A(z), .B(q[0]), .Y(g));
  BUFx2_ASAP7_75t_R _6_ (.A(z), .Y(s[0]));
  BUFx2_ASAP7_75t_R _7_ (.A(z), .Y(s[1]));
endmodule
"""


def test_declared_spare_out_bits_tied_constant(tmp_path):
    """DIE-S81-46 seqhost__t1 (COORD 10-30 14:0x (2)(b)): the kit-rtl wrapper ties the 2 plan-only bits of unit_o4 to 0;
    Yosys shares the TIELO net with internal logic, so face_guard saw 'shared'.  Declared bits pass as spare_declared;
    undeclared constant bits and declared bits that are not tied keep failing."""
    r = face_guard.guard(NET_SPARE)
    assert r["fail_counts"].get("shared") == 2 and "spare_declared" not in r, r
    r = face_guard.guard(NET_SPARE, spare=["s[0]", "s[1]"])
    assert r["verdict"] == "PASS" and sorted(r["spare_declared"]) == ["s[0]", "s[1]"], r
    r = face_guard.guard(NET_SPARE, spare=["s[0]"])                     # s[1] not declared: still fails
    assert r["fail_counts"] == {"shared": 1} and r["spare_declared"] == ["s[0]"], r
    r = face_guard.guard(NET_SPARE, spare=["s[0]", "s[1]", "o[0]"])     # a registered bit declared spare: ordinary
    assert r["verdict"] == "PASS" and "o[0]" not in r["spare_declared"] and "o[0]" in r["flops"], r
    logic = NET_SPARE.replace("BUFx2_ASAP7_75t_R _6_ (.A(z)", "BUFx2_ASAP7_75t_R _6_ (.A(g)")
    r = face_guard.guard(logic, spare=["s[0]", "s[1]"])                 # logic-driven declared bit: not a tie
    assert r["verdict"] == "FAIL" and r["spare_declared"] == ["s[1]"], r
    with pytest.raises(ValueError):
        face_guard.spare_out_list(dict(schema="x", bits=["s[0]"]))
    with pytest.raises(ValueError):
        face_guard.spare_out_list(dict(schema=face_guard.SPARE_SCHEMA, bits=["s[0]", "s[0]"]))
    assert face_guard.kit_spare_list(tmp_path) == []
    (tmp_path / "spare_out.json").write_text(json.dumps(dict(schema=face_guard.SPARE_SCHEMA, bits=["s[0]", "s[1]"])))
    assert face_guard.kit_spare_list(tmp_path) == ["s[0]", "s[1]"]


def test_gen_phys_spare_out_bits_from_kit_rtl(tmp_path):
    import gen_phys
    fl = tmp_path / "kit_rtl.f"
    fl.write_text("")
    assert gen_phys.kit_spare_out_bits(fl) == []                        # no kit_rtl.json: no file, no bits
    kj = tmp_path / "kit_rtl.json"
    kj.write_text(json.dumps(dict(spare_out_bits=[dict(port="unit_o4", bits=2), dict(port="lane_o", bits=3)],
                                  narrow_buses=[dict(port="unit_o4", plan=267, bound=265)])))
    assert gen_phys.kit_spare_out_bits(fl) == ["unit_o4[265]", "unit_o4[266]", "lane_o[0]", "lane_o[1]", "lane_o[2]"]
    kj.write_text(json.dumps(dict(spare_out_bits=[dict(port="unit_o4", bits=3)],
                                  narrow_buses=[dict(port="unit_o4", plan=267, bound=265)])))
    with pytest.raises(gen_rtl.GenError):
        gen_phys.kit_spare_out_bits(fl)


def test_declared_timed_face_buses(tmp_path):
    """DIE-KV-61/hr 11-02: a declared timed-face bus turns unregistered/shared/dropped/const findings into
    timed_declared; feedthrough and undeclared buses keep failing; the file is fail-closed."""
    comb = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));",
                          "NAND2x1_ASAP7_75t_R _3_ (.A(_1_), .B(_0_), .Y(o[1]));")
    assert face_guard.guard(comb)["verdict"] == "FAIL"
    r = face_guard.guard(comb, timed=["o"])
    assert r["verdict"] == "PASS" and r["timed_declared"] and r["timed_declared"][0].startswith("o[1]"), r
    assert face_guard.guard(comb, timed=["a"])["verdict"] == "FAIL"          # other bus declared: still fails
    shared = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "INVx3_ASAP7_75t_R _3_ (.A(_0_), .Y(o[1]));")
    assert face_guard.guard(shared, timed=["o"])["verdict"] == "PASS"
    dropped = NET_OK.replace(".D(a[1])", ".D(q[0])")
    assert face_guard.guard(dropped, timed=["a"])["verdict"] == "PASS"
    feed = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "assign o[1] = a[1];")
    assert "feedthrough" in face_guard.guard(feed, timed=["o", "a"])["fail_counts"]
    doc = dict(schema=face_guard.TIMED_SCHEMA, buses=["o"], ruling="r", reason="x")
    assert face_guard.timed_face_list(doc) == ["o"]
    for bad in (dict(doc, schema="x"), dict(doc, buses=["o[1]"]), dict(doc, buses=[]), dict(doc, ruling=""),
                dict(doc, buses=["o", "o"]), dict(doc, reason=None)):
        with pytest.raises(ValueError):
            face_guard.timed_face_list(bad)
    (tmp_path / "timed_face.json").write_text(json.dumps(doc))
    assert face_guard.kit_timed_list(tmp_path) == ["o"]
    assert face_guard.kit_timed_list(tmp_path / "none") == []


def test_declared_intra_pair_seam(tmp_path):
    """HBM-Q2NF-RF 11-10 (COORD, Q2NF split): a declared seam bus turns its shared / unregistered findings into
    seam_declared; a merged flop passes only with at most ONE non-seam bit; feedthrough, undeclared and die-facing
    buses keep failing; the file is fail-closed."""
    seam = {"ft0_o": frozenset({"merged"})}
    assert face_guard.guard(NET_FT1)["verdict"] == "FAIL"
    r = face_guard.guard(NET_FT1, ft1={"ft1"}, seam=seam)          # ft0: in-face (die) + out-face (seam) share a flop
    assert r["verdict"] == "PASS" and len(r["seam_declared"]) == 4 and r["ok"] == 6, r
    assert face_guard.guard(NET_FT1, ft1={"ft1"}, seam={"ft0_o": frozenset({"shared"})})["fail_counts"] == {"merged": 4}
    two = NET_FT1.replace(".QN(ft1_o));", ".QN(ft1_o));\n  INVx1_ASAP7_75t_R _9_ (.A(ft0_o[0]), .Y(x_o));") \
        .replace("output ft1_o;", "output ft1_o; output x_o;").replace("(clk, ft0_i,", "(clk, x_o, ft0_i,")
    assert face_guard.guard(two, ft1={"ft1"}, seam=seam)["verdict"] == "FAIL"   # extra load: still a finding
    comb = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));",
                          "NAND2x1_ASAP7_75t_R _3_ (.A(_1_), .B(_0_), .Y(o[1]));")
    r = face_guard.guard(comb, seam={"o": frozenset({"unregistered", "shared"})})
    assert r["verdict"] == "PASS" and r["seam_declared"], r
    assert face_guard.guard(comb, seam={"o": frozenset({"merged"})})["verdict"] == "FAIL"
    assert face_guard.guard(comb, seam={"a": frozenset({"unregistered", "shared"})})["verdict"] == "FAIL"
    feed = NET_OK.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));", "assign o[1] = a[1];")
    assert "feedthrough" in face_guard.guard(feed, seam={"o": frozenset(face_guard.SEAM_CLASSES),
                                                         "a": frozenset(face_guard.SEAM_CLASSES)})["fail_counts"]
    doc = dict(schema=face_guard.SEAM_SCHEMA, partner="ot_q2nf_lk", buses={"o": ["shared", "merged"]},
               ruling="COORD 11-10", reason="intra-pair seam, timed by pair STA")
    assert face_guard.seam_face_map(doc) == {"o": frozenset({"shared", "merged"})}
    for bad in (dict(doc, schema="x"), dict(doc, partner=""), dict(doc, buses={}), dict(doc, buses={"o[1]": ["shared"]}),
                dict(doc, buses={"o": []}), dict(doc, buses={"o": ["feedthrough"]}), dict(doc, buses={"o": ["shared", "shared"]}),
                dict(doc, buses=["o"]), dict(doc, ruling=""), dict(doc, reason=None)):
        with pytest.raises(ValueError):
            face_guard.seam_face_map(bad)
    (tmp_path / "seam_face.json").write_text(json.dumps(doc))
    assert face_guard.kit_seam_map(tmp_path) == {"o": frozenset({"shared", "merged"})}
    assert face_guard.kit_seam_map(tmp_path / "none") == {}


def test_face_lockup_latch_flop_latch_port():
    """S81-RF1 (DIE-S81-51/CLK 11-03): flop -> ONE transparent-low latch (DLLx1 / $_DLATCH_N_) -> port is a registered
    face; a second latch, a high-transparent latch or a latch with fan-out is not."""
    lat = NET_OK.replace("INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));",
                         "DLLx1_ASAP7_75t_R \\u_l.o_l[0]$_DLATCH_N_  (.CLK(clk), .D(_0_), .Q(o[0]));")
    pins = [dict(bus="a", bit=0), dict(bus="a", bit=1), dict(bus="o", bit=0), dict(bus="o", bit=1)]
    r = face_guard.guard(lat, pins=pins)
    assert r["verdict"] == "PASS" and r["ok"] == 4 and r["face_lockup"] == ["o[0]"], r
    yl = lat.replace("DLLx1_ASAP7_75t_R \\u_l.o_l[0]$_DLATCH_N_  (.CLK(clk), .D(_0_), .Q(o[0]));",
                     "\\$_DLATCH_N_ \\u_l.o_l[0]  (.E(clk), .D(_0_), .Q(o[0]));")
    assert face_guard.guard(yl, pins=pins)["verdict"] == "PASS"
    hi = lat.replace("DLLx1_ASAP7_75t_R", "DHLx1_ASAP7_75t_R")
    assert "unregistered" in face_guard.guard(hi, pins=pins)["fail_counts"]
    two = lat.replace(".D(_0_), .Q(o[0]));", ".D(_9_), .Q(o[0]));\n  DLLx1_ASAP7_75t_R \\u_l2  (.CLK(clk), .D(_0_), .Q(_9_));") \
        .replace("wire _0_;", "wire _0_; wire _9_;")
    assert "unregistered" in face_guard.guard(two, pins=pins)["fail_counts"]
    fan = lat.replace("INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));",
                      "INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));\n  INVx1_ASAP7_75t_R _4_ (.A(o[0]), .Y(_8_));") \
        .replace("wire _0_;", "wire _0_; wire _8_;")
    assert face_guard.guard(fan, pins=pins)["verdict"] != "PASS"


def test_face_lockup_latch_polarity_clock_and_logic_mutants():
    """FLOW-LATCH-1 (11-03): the face lockup latch is accepted only transparent-low on the face flop's own clock
    (DLL on clk, or DHL on INV(clk)); wrong polarity, another clock, a falling-edge face flop or logic between the
    face flop and the latch are each unregistered."""
    lat = NET_OK.replace("INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));",
                         "DLLx1_ASAP7_75t_R \\u_l.o_l[0]  (.CLK(clk), .D(_0_), .Q(o[0]));")
    pins = [dict(bus="a", bit=0), dict(bus="a", bit=1), dict(bus="o", bit=0), dict(bus="o", bit=1)]

    def fails(net):
        r = face_guard.guard(net, pins=pins)
        return r["verdict"], [x for x in r["fails"].get("unregistered", []) if x.startswith("o[0]")]

    assert fails(lat) == ("PASS", [])
    # negative-level via a DHL on the inverted, buffered clock (how synthesis may fold `if (!clk)`)
    inv = lat.replace("DLLx1_ASAP7_75t_R \\u_l.o_l[0]  (.CLK(clk),",
                      "INVx1_ASAP7_75t_R ick (.A(clk), .Y(clk_n));\n  BUFx2_ASAP7_75t_R bck (.A(clk_n), .Y(clk_nb));\n"
                      "  DHLx1_ASAP7_75t_R \\u_l.o_l[0]  (.CLK(clk_nb),").replace("wire _0_;", "wire _0_; wire clk_n, clk_nb;")
    assert fails(inv) == ("PASS", []), face_guard.guard(inv, pins=pins)["fails"]
    # WRONG POLARITY: DLL on the inverted clock = transparent while clk is high
    wp = inv.replace("DHLx1_ASAP7_75t_R \\u_l.o_l[0]", "DLLx1_ASAP7_75t_R \\u_l.o_l[0]")
    v, f = fails(wp)
    assert v == "FAIL" and f and "transparent-high" in f[0], f
    # WRONG POLARITY: DHL / $_DLATCH_P_ on clk
    for hi in (lat.replace("DLLx1_ASAP7_75t_R", "DHLx1_ASAP7_75t_R"),
               lat.replace("DLLx1_ASAP7_75t_R \\u_l.o_l[0]  (.CLK(clk),", "\\$_DLATCH_P_ \\u_l.o_l[0]  (.E(clk),")):
        v, f = fails(hi)
        assert v == "FAIL" and f and "transparent-high" in f[0], f
    # ANOTHER CLOCK: latch enable is not the face flop clock
    oc = lat.replace("input clk;", "input clk; input clk2;").replace("module top(clk, a, o);", "module top(clk, clk2, a, o);") \
        .replace("(.CLK(clk), .D(_0_), .Q(o[0]))", "(.CLK(clk2), .D(_0_), .Q(o[0]))")
    v, f = fails(oc)
    assert v == "FAIL" and f and "not the face flop clock" in f[0], f
    # FALLING-EDGE face flop behind the latch
    fe = lat.replace("DFFHQNx1_ASAP7_75t_R \\u_bout_o.q[0]$_DFF_P_ ", "DFFLQNx1_ASAP7_75t_R \\u_bout_o.q[0]$_DFF_N_ ")
    v, f = fails(fe)
    assert v == "FAIL" and f and "not rising-edge" in f[0], f
    # COMBINATIONAL LOGIC feeding the latch (flop -> AND -> latch -> port)
    cl = lat.replace("(.CLK(clk), .D(_0_), .Q(o[0]))", "(.CLK(clk), .D(_7_), .Q(o[0]))") \
        .replace("wire _0_;", "wire _0_; wire _7_;") \
        .replace("endmodule", "  AND2x2_ASAP7_75t_R g7 (.A(_0_), .B(a[1]), .Y(_7_));\nendmodule")
    v, f = fails(cl)
    assert v == "FAIL" and f and "driven by AND2x2" in f[0], f


# ---- DIE-S81-51/SPARE 11-03: spare plan bits of narrow buses (KW-FIX-4 'dropped' / 'land_slot' class) -------------
NET_LAND_SPARE = r"""
module top(ck, e, x, o, s);
  input ck; input e; input [1:0] x; output o; output [1:0] s;
  wire g0; wire g1; wire q0; wire q1; wire _0_; wire z; wire g;
  ICGx1_ASAP7_75t_R u_cg0 (.CLK(ck), .ENA(e), .SE(1'b0), .GCLK(g0));
  ICGx1_ASAP7_75t_R u_cg1 (.CLK(ck), .ENA(e), .SE(1'b0), .GCLK(g1));
  DFFHQNx1_ASAP7_75t_R s0 (.CLK(g0), .D(x[0]), .QN(q0));
  DFFHQNx1_ASAP7_75t_R s1 (.CLK(g1), .D(x[0]), .QN(q1));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q$_DFF_P_ (.CLK(ck), .D(q0), .QN(_0_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o));
  TIELOx1_ASAP7_75t_R _4_ (.L(z));
  BUFx2_ASAP7_75t_R _6_ (.A(z), .Y(s[0]));
  BUFx2_ASAP7_75t_R _7_ (.A(z), .Y(s[1]));
endmodule
"""


def test_narrow_input_spare_bit_dead_declared_pass():
    """narrow plan input: the spare bit a[1] has no load in the kit-rtl wrapper -> declared dead -> PASS."""
    dropped = NET_OK.replace(".D(a[1])", ".D(q[0])")
    assert face_guard.guard(dropped)["fail_counts"] == {"dropped": 1}
    r = face_guard.guard(dropped, dead=["a[1]"])
    assert r["verdict"] == "PASS" and r["dead_declared"] == ["a[1]"], r


def test_narrow_landing_ft_spare_bits_dead_and_spare_out_pass():
    """narrow ft slot on a declared LANDING bus x (D 2): spare _i bit x[1] unread (dead), spare _o bits s tied 0
    (spare_out) -> PASS; undeclared it is the KW-FIX-4 land_slot class '0 loads on x[1], declared D 2'."""
    r = face_guard.guard(NET_LAND_SPARE, "top", skip_re=SKIP_LAND, land={"x": 2})
    assert r["verdict"] == "FAIL" and "land_slot" in r["fail_counts"], r
    r = face_guard.guard(NET_LAND_SPARE, "top", skip_re=SKIP_LAND, land={"x": 2}, dead=["x[1]"],
                         spare=["s[0]", "s[1]"])
    assert r["verdict"] == "PASS" and r["dead_declared"] == ["x[1]"] and r["land_slot_bits"] == 1, r.get("fails")


@pytest.mark.parametrize("mut", [
    "  AND2x2_ASAP7_75t_R _9_ (.A(x[1]), .B(q0), .Y(g));\n",                  # spare bit wired into logic
    "  DFFHQNx1_ASAP7_75t_R s9 (.CLK(ck), .D(x[1]), .QN(g));\n",              # spare bit into a (station) flop
])
def test_declared_dead_spare_bit_with_a_load_fails(mut):
    """a declared dead spare bit that still loads anything FAILs class dead (never a silent pass)."""
    net = NET_LAND_SPARE.replace("endmodule", mut + "endmodule")
    r = face_guard.guard(net, "top", skip_re=SKIP_LAND, land={"x": 2}, dead=["x[1]"], spare=["s[0]", "s[1]"])
    assert r["verdict"] == "FAIL" and r["fail_counts"].get("dead") == 1 and r["dead_declared"] == [], r
    dropped = NET_OK.replace(".D(a[1])", ".D(q[0])").replace("endmodule", mut.replace("x[1]", "a[1]") + "endmodule")
    r = face_guard.guard(dropped, dead=["a[1]"])
    assert r["verdict"] == "FAIL" and r["fail_counts"].get("dead") == 1, r


def test_main_reads_generated_dead_inputs_beside_pins(tmp_path):
    """face_guard CLI (run_kit.sh) reads the generated kit dead_inputs.json / spare_out.json beside pins.json."""
    (tmp_path / "net.v").write_text(NET_OK.replace(".D(a[1])", ".D(q[0])"))
    (tmp_path / "pins.json").write_text("[]")
    fg = tmp_path / "fg.json"
    assert face_guard.main([str(tmp_path / "net.v"), "--pins", str(tmp_path / "pins.json"), "--out", str(fg)]) != 0
    (tmp_path / "dead_inputs.json").write_text(json.dumps(dict(
        schema=face_guard.DEAD_SCHEMA, bits=["a[1]"],
        proof=dict(verdict="PASS", method="bind.py kit-rtl: plan bits beyond the bound payload width are not "
                   "connected in the generated wrapper", receipt=dict(wrapper="w.sv", sha256="0" * 64,
                                                                       narrow_buses=[dict(port="a", plan=2, bound=1)])))))
    assert face_guard.main([str(tmp_path / "net.v"), "--pins", str(tmp_path / "pins.json"), "--out", str(fg)]) == 0
    assert json.loads(fg.read_text())["dead_declared"] == ["a[1]"]


def _local_reset_leaf_vehicle(leaf):
    """DIE-QC-84 11-06 (QC slw_fw_v2 START4): the face copy samples the start under its OWN local reset leaf, an
    equal-depth reset relay copy of the origin's reset root (ot_dp_rrelay, 'local same-cycle reset copy')."""
    text, spec = _relay_copy_vehicle()
    text = text.replace("ot_dp_landing_relay copy0", leaf + " ot_dp_landing_relay copy0")
    return text.replace("copy0 (.clk(clk), .st(st), .rq(rq)", "copy0 (.clk(clk), .st(st), .rq(rq2)"), spec


def test_relay_copy_on_equal_depth_local_reset_leaf_passes():
    text, spec = _local_reset_leaf_vehicle(f"DFFHQNx1{_X} reset_ff2 (.CLK(clk), .D(rst_n), .QN(rq2));")
    got = face_guard.guard(text, "top", land=spec)
    assert got["verdict"] == "PASS", got["fails"]
    assert got["ring_start"]["st"]["face_copies"] == {"copy0": "o0", "copy1": "o1"}


@pytest.mark.parametrize("leaf", [
    # one cycle later than the origin's reset leaf
    f"DFFHQNx1{_X} r2a (.CLK(clk), .D(rst_n), .QN(r2a)); INVx1{_X} r2i (.A(r2a), .Y(r2b)); "
    f"DFFHQNx1{_X} reset_ff2 (.CLK(clk), .D(r2b), .QN(rq2));",
    # another root
    f"DFFHQNx1{_X} reset_ff2 (.CLK(clk), .D(st), .QN(rq2));",
    # another clock
    f"DFFHQNx1{_X} reset_ff2 (.CLK(st), .D(rst_n), .QN(rq2));",
    # inverted parity
    f"DFFHQNx1{_X} r2a (.CLK(clk), .D(rst_n), .QN(r2a)); INVx1{_X} reset_inv2 (.A(r2a), .Y(rq2));",
])
def test_relay_copy_local_reset_leaf_mutants_fail_closed(leaf):
    text, spec = _local_reset_leaf_vehicle(leaf)
    assert face_guard.guard(text, "top", land=spec)["verdict"] == "FAIL", leaf


# ---- S81-GUNIT-FORM-1 11-07: land form "replica" (D kept replica pin registers, no logic, any buffer tree)
def _rep_net(tree):
    return ("module top(clk, a, o);\n  input clk; input a; output o; wire b1; wire b2; wire q0; wire q1; wire q2; wire x; wire oq;\n"
            + tree +
            f"  AND3x1{_X} g (.A(q0), .B(q1), .C(q2), .Y(x));\n"
            f"  DFFHQNx1{_X} fo (.CLK(clk), .D(x), .QN(oq));\n  INVx3{_X} io (.A(oq), .Y(o));\nendmodule\n")


_REP_OK = (f"  BUFx2{_X} t0 (.A(a), .Y(b1));\n"
           f"  DFFHQNx1{_X} r0 (.CLK(clk), .D(a), .QN(q0));\n"
           f"  DFFHQNx1{_X} r1 (.CLK(clk), .D(b1), .QN(q1));\n"
           f"  DFFHQNx1{_X} r2 (.CLK(clk), .D(b1), .QN(q2));\n")


_RP = "s81/delta_gunit_l1f_band_1107"


def _rep(d, plan=_RP):
    return {"D": d, "form": "replica", "plan": plan}


def test_land_replica_form(monkeypatch):
    monkeypatch.setitem(face_guard.REPLICA_PLANS, _RP, ("top",))
    assert face_guard.land_spec(_rep(3)) == (3, "replica")
    net = _rep_net(_REP_OK)
    assert face_guard.guard(net, "top")["verdict"] == "FAIL"                       # plain rule: shared
    r = face_guard.guard(net, "top", land={"a": _rep(3)})
    assert r["verdict"] == "PASS" and r["land_replica_bits"] == 1, r["fails"]
    assert face_guard.guard(net, "top", land={"a": _rep(2)})["verdict"] == "FAIL"
    odd = _REP_OK.replace(f"BUFx2{_X} t0", f"INVx2{_X} t0")                          # odd inversion
    assert face_guard.guard(_rep_net(odd), "top", land={"a": _rep(3)})["verdict"] == "FAIL"
    logic = _REP_OK.replace(f"BUFx2{_X} t0 (.A(a), .Y(b1))", f"AND2x2{_X} t0 (.A(a), .B(clk), .Y(b1))")
    assert face_guard.guard(_rep_net(logic), "top", land={"a": _rep(3)})["verdict"] == "FAIL"


def test_land_replica_opt_in_keyed_by_plan(monkeypatch):
    """COORD 11-07 23:3x: replica is opt-in, keyed by the plan; anything else fails closed and no other form moves."""
    assert "replica" not in face_guard.LAND_FORMS                                    # not a generic form
    assert face_guard.REPLICA_PLANS[_RP] == ("dsdv_gunit_l1f_bf",)                  # v5 provider plan: own test
    net = _rep_net(_REP_OK)
    for bad in ({"D": 3, "form": "replica"}, _rep(3, "s81/other_plan"), dict(_rep(3), extra=1), _rep(1)):
        with pytest.raises(ValueError):
            face_guard.land_spec(bad)
        with pytest.raises(ValueError):
            face_guard.guard(net, "top", land={"a": bad})
    with pytest.raises(ValueError, match="does not list top"):                    # listed plan, other top
        face_guard.guard(net, "top", land={"a": _rep(3)})
    monkeypatch.setitem(face_guard.REPLICA_PLANS, _RP, ("top",))
    assert face_guard.guard(net, "top", land={"a": _rep(3)})["verdict"] == "PASS"
    # the other land forms are unchanged
    assert face_guard.land_spec(3) == (3, "icg")
    assert face_guard.land_spec({"D": 2, "form": "hold_mux"}) == (2, "hold_mux")
    with pytest.raises(ValueError):
        face_guard.land_spec({"D": 2, "form": "hold_mux", "plan": _RP})


# ---- S81-SVCRS-3 11-10 (COORD ruling): replica form with a per-bit D map ("bits"), keyed by the v5 provider plan
_RPV5 = "s81/svc_prov_1109_v5"


def _bits_net(copies_bit1):
    """bus a[1:0]: bit 0 one face register, bit 1 in `copies_bit1` replica registers"""
    regs = "".join(f"  DFFHQNx1{_X} r1_{k} (.CLK(clk), .D(a[1]), .QN(q1_{k}));\n" for k in range(copies_bit1))
    qs = " ".join(f"wire q1_{k};" for k in range(copies_bit1))
    ins = ", ".join([".A(q0)"] + [f".{'BCD'[k]}(q1_{k})" for k in range(copies_bit1)])
    gate = {1: "AND2x2", 2: "AND3x1", 3: "AND4x1"}[copies_bit1]
    return (f"module top(clk, a, o);\n  input clk; input [1:0] a; output o; wire q0; {qs} wire x; wire oq;\n"
            f"  DFFHQNx1{_X} r0 (.CLK(clk), .D(a[0]), .QN(q0));\n" + regs +
            f"  {gate}{_X} g ({ins}, .Y(x));\n"
            f"  DFFHQNx1{_X} fo (.CLK(clk), .D(x), .QN(oq));\n  INVx3{_X} io (.A(oq), .Y(o));\nendmodule\n")


def _rb(bits, plan=_RPV5):
    return {"bits": bits, "form": "replica", "plan": plan}


def test_land_replica_per_bit_map(monkeypatch):
    monkeypatch.setitem(face_guard.REPLICA_PLANS, _RPV5, ("top",))
    net = _bits_net(2)
    assert face_guard.guard(net, "top")["verdict"] == "FAIL"                        # plain rule: a[1] shared
    r = face_guard.guard(net, "top", land={"a": _rb({"1": 2})})
    assert r["verdict"] == "PASS" and r["land_replica_bits"] == 1, r["fails"]       # a[0] stays a plain face bit
    assert face_guard.guard(net, "top", land={"a": _rb({"1": 3})})["verdict"] == "FAIL"   # wrong D
    assert face_guard.guard(net, "top", land={"a": _rb({"0": 2, "1": 2})})["verdict"] == "FAIL"  # a[0] has 1 flop
    assert face_guard.guard(net, "top", land={"a": _rb({"5": 2})})["verdict"] == "FAIL"   # not a bit of a
    assert face_guard.guard(_bits_net(1), "top", land={"a": _rb({"1": 2})})["verdict"] == "FAIL"


def test_land_replica_per_bit_fails_closed(monkeypatch):
    monkeypatch.setitem(face_guard.REPLICA_PLANS, _RPV5, ("top",))
    for bad in (_rb({}), _rb({"1": 1}), _rb({"x": 2}), _rb({"1": True}), _rb({"1": 2}, "s81/other_plan"),
                dict(_rb({"1": 2}), D=2)):
        with pytest.raises(ValueError):
            face_guard.land_spec(bad)
    assert face_guard.land_spec(_rb({"1": 2, "3": 5})) == (5, "replica")


def test_replica_plans_v5_provider_tops():
    assert face_guard.REPLICA_PLANS[_RPV5] == ("ot_s81_su_smd_fold2", "ot_s81_su_sml_fold2", "ot_hdc_v41x_attn_tr_x")
