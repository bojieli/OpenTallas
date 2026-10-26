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
