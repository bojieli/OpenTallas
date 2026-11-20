"""LOCKUP-STATION-1130 (FABLE-CLOSURE-1315 (2)): a transparent-low lockup latch whose data comes from a hard-core
(black-box) OUTPUT pin is a wire in the cycle model: the stub models the pin as a free self-loop flop
'<inst>.lec_bbo_<pin>' (stub_verilog) that never changes, so the latch passes the same value in both phases.  Before
this rule lec.py refused it ("latch gold: ... data reads $_DFF_P_ u_dut.u_bound.u_u_lf1_u_vp_g_ln_15_u_l.lec_bbo_o[15]
(not a rising-edge flop on a primary-input clock)", S81 leaf t39 lockup proof).  ok (latch in the gate only) and rtl
(latch on both sides) are EQUIVALENT; the mutant that captures one bit from the wrong pin is NOT EQUIVALENT.
The integration tests need docker + the ORFS image.
    python3 -m pytest -q tools/die_plan/test_lec_bbo_lockup.py"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

GOLD = """module kid(input wire ck, input wire [1:0] s, output wire [1:0] y);
  reg [1:0] q;
  always @(posedge ck) q <= s;
  assign y = q;
endmodule
module lec_bbo_t(input wire clk, input wire [1:0] d, output wire [1:0] o);
  wire [1:0] k;
  reg [1:0] r;
  kid u_kid(.ck(clk), .s(d), .y(k));
LATCH
  always @(posedge clk) r <= SRC;
  assign o = r;
endmodule
"""
RTL_LATCH = "  reg [1:0] lk;\n  always @(*) if (!clk) lk = k;"


def _gate(mut=False):
    s = ["module lec_bbo_t(clk, d, o);", "  input clk; input [1:0] d; output [1:0] o;", "  wire [1:0] k, l, rn;",
         "  kid u_kid (.ck(clk), .s(d), .y(k));"]
    for i in range(2):
        src = f"k[{1 - i}]" if mut and i == 0 else f"k[{i}]"
        s += [f"  DLLx1_ASAP7_75t_R u_fl_nl_{i} (.CLK(clk), .D({src}), .Q(l[{i}]));",
              f"  DFFHQNx1_ASAP7_75t_R \\r[{i}]$_DFF_P_ (.CLK(clk), .D(l[{i}]), .QN(rn[{i}]));",
              f"  INVx1_ASAP7_75t_R u_i{i} (.A(rn[{i}]), .Y(o[{i}]));"]
    s += ["endmodule", ""]
    return "\n".join(s)


KIT_LIB = """library (kid_tt) {
  type (bus_1_0) { base_type : array; data_type : bit; bit_width : 2; bit_from : 1; bit_to : 0; downto : true; }
  cell (kid) {
    area : 1;
    pin (ck) { direction : input; clock : true; }
    bus (s) { bus_type : bus_1_0; direction : input; }
    bus (y) { bus_type : bus_1_0; direction : output; }
  }
}
"""


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")


def _kit(tmp_path, name, rtl_latch=False, mut=False):
    k = tmp_path / name
    (k / "rtl").mkdir(parents=True)
    (k / "macros").mkdir()
    g = GOLD.replace("LATCH", RTL_LATCH if rtl_latch else "").replace("SRC", "lk" if rtl_latch else "k")
    (k / "rtl" / "lec_bbo_t.sv").write_text(g)
    (k / "macros" / "kid_tt.lib").write_text(KIT_LIB)
    n = k / "run" / "results" / "asap7" / "lec_bbo_t" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(_gate(mut))
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_bbo_t\nexport PLATFORM = asap7\n"
        "export VERILOG_FILES = /work/rtl/lec_bbo_t.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\n"
        "export VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\n"
        "export ADDITIONAL_LIBS = /work/macros/kid_tt.lib\n")
    return k


def _run(kit):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900)
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


def test_bb_free_out_only_for_self_holding_stub_flops():
    assert lec.bb_free_out({"connections": {"D": [7], "Q": [7], "C": [2]}}, "u_dut.u_kid.lec_bbo_y[0]$_DFF_P_")
    assert not lec.bb_free_out({"connections": {"D": [5], "Q": [7], "C": [2]}}, "u_dut.u_kid.lec_bbo_y[0]$_DFF_P_")
    assert not lec.bb_free_out({"connections": {"D": [7], "Q": [7], "C": [2]}}, "u_dut.r[0]$_DFF_P_")


@needs_image
def test_gate_latch_after_blackbox_output_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r.get("reason")


@needs_image
def test_latch_on_both_sides_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "rtl", rtl_latch=True))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r.get("reason")


@needs_image
def test_latch_reading_the_wrong_pin_is_not_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "mut", mut=True))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r.get("reason")
