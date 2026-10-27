"""face_guard (CP1-R10, COORD 10-24): every planned face register survives Yosys as its own flop.
    python3 -m pytest -q tools/die_plan/test_face_guard.py"""
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
