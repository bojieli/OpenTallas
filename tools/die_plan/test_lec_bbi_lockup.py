"""QC-NK-HOLD 11-11 (bind clock.core_input_lockup, QC NK hold class form A): a transparent-low lockup latch between a
rising-edge flop and a hard-core (black-box) input pin is a wire in the cycle model: the core samples its pins at its
own rising edge, exactly like a rising-edge flop of ours.  Before this rule lec.py refused it as UNPROVEN ("latch
gate: ... Q reaches $_DFF_P_ u_dut.u_t32.lec_bbi_n_b[513]$_DFF_P_.D"; cbn_q11 pilot 1).  ok (latch in the gate only)
and rtl (the ot_dp_lk form on both sides) are EQUIVALENT; the mutant whose latch reads the input instead of the flop
is NOT EQUIVALENT.  The integration tests need docker + the ORFS image.
    python3 -m pytest -q tools/die_plan/test_lec_bbi_lockup.py"""
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
module lec_bbi_t(input wire clk, input wire clk_c, input wire [1:0] d, output wire [1:0] o);
  reg [1:0] r;
  always @(posedge clk) r <= d;
LATCH
  kid u_kid(.ck(clk_c), .s(KID_S), .y(o));
endmodule
"""
RTL_LATCH = "  reg [1:0] lk;\n  always @(*) if (!clk) lk = r;"


def _gate(mut=False):
    src = "d" if mut == True else "r0"
    s = ["module lec_bbi_t(clk, clk_c, d, o);", "  input clk; input clk_c; input [1:0] d; output [1:0] o;",
         "  wire [1:0] rn, r0, l;"]
    for i in range(2):
        s += [f"  DFFHQNx1_ASAP7_75t_R \\r[{i}]$_DFF_P_ (.CLK(clk), .D(d[{i}]), .QN(rn[{i}]));",
              f"  INVx1_ASAP7_75t_R u_i{i} (.A(rn[{i}]), .Y(r0[{i}]));",
              f"  DLLx1_ASAP7_75t_R u_lk_nk_{i} (.CLK(clk), .D({src}[{i}]), .Q(l[{i}]));"]
    kid_s = "{l[0], l[1]}" if mut == "QSWAP" else "l"   # wrong Q connection: latch bits crossed at the pin
    s += [f"  kid u_kid (.ck(clk_c), .s({kid_s}), .y(o));", "endmodule", ""]
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
    g = GOLD.replace("LATCH", RTL_LATCH if rtl_latch else "").replace("KID_S", "lk" if rtl_latch else "r")
    (k / "rtl" / "lec_bbi_t.sv").write_text(g)
    (k / "macros" / "kid_tt.lib").write_text(KIT_LIB)
    n = k / "run" / "results" / "asap7" / "lec_bbi_t" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(_gate(mut))
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_bbi_t\nexport PLATFORM = asap7\n"
        "export VERILOG_FILES = /work/rtl/lec_bbi_t.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\n"
        "export VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\n"
        "export ADDITIONAL_LIBS = /work/macros/kid_tt.lib\n")
    return k


def _run(kit):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900)
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


def test_rule_is_in_the_latch_fanout_check():
    src = (HERE / "lec.py").read_text()
    assert "def bbi_ff(cn, latch_clock, latch_phase):" in src and '(bbi_ff(ln, e, phase[cn]) and lp == "D")' in src


@needs_image
def test_gate_latch_into_blackbox_pin_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r.get("reason")
    assert r["lockup_latches"]["gate"]["to_wire"] == 2, r


@needs_image
def test_latch_on_both_sides_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "rtl", rtl_latch=True))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r.get("reason")


@needs_image
def test_latch_reading_the_input_is_not_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "mut", mut=True))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r.get("reason")


@needs_image
def test_latch_q_crossed_at_the_pin_is_not_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "qswap", mut="QSWAP"))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r.get("reason")
    assert sorted(e["point"] for e in r["failing"]) == ["bb:u_dut.u_kid.lec_bbi_s[0]", "bb:u_dut.u_kid.lec_bbi_s[1]"], r
