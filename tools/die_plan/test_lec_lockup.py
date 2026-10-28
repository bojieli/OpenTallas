"""lec.py lockup-latch abstraction (latch_to_wire, LEC-FPREG-3 2026-10-27): a transparent-low ASAP7 DLL latch
between rising-edge flops is a wire in the cycle model.  ok: r0 -> DLL -> r1 is EQUIVALENT to the RTL r0 -> r1;
mutants (the latch reads the input instead of r0, the latch dropped and r1 reads r0's input) are NOT EQUIVALENT;
topologies outside the abstraction (transparent-high DHL, a latch clocked by an inverted clock or by a data input,
Q to a falling-edge flop, Q to a module output) are UNPROVEN, never EQUIVALENT; OT_LEC_LATCH=0 refuses latches."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

RTL = """module lec_lk_t (input clk, input [1:0] a, input b, output [1:0] y, output z);
  reg [1:0] r0, r1;
  reg n0, n1;
  always @(posedge clk) begin r0 <= a; r1 <= r0; n0 <= b; end
  always @(negedge clk) n1 <= n0;
  assign y = r1;
  assign z = n1;
endmodule
"""


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")


def _netlist(v):
    lat = {"DHL": "DHLx1_ASAP7_75t_R"}.get(v, "DLLx1_ASAP7_75t_R")
    s = ["module lec_lk_t(clk, a, b, y, z);", "  input clk; input [1:0] a; input b; output [1:0] y; output z;",
         "  wire [1:0] q0n, q0, l, yn; wire nclk, n0n, n0, ln, n1n;",
         "  INVx1_ASAP7_75t_R ick (.A(clk), .Y(nclk));"]
    for i in range(2):
        lclk = "nclk" if v == "INV" else ("b" if v == "DATACLK" else "clk")
        ld = f"a[{i}]" if v == "MUT_SKIP" else f"q0[{i}]"
        s += [f"  DFFHQNx1_ASAP7_75t_R \\r0[{i}]$_DFF_P_ (.CLK(clk), .D(a[{i}]), .QN(q0n[{i}]));",
              f"  INVx1_ASAP7_75t_R i0_{i} (.A(q0n[{i}]), .Y(q0[{i}]));"]
        if v == "MUT_DROP":
            s += [f"  BUFx2_ASAP7_75t_R lk_{i} (.A(a[{i}]), .Y(l[{i}]));"]
        else:
            s += [f"  {lat} lk_{i} (.CLK({lclk}), .D({ld}), .Q(l[{i}]));"]
        if v == "PO" and i == 1:
            s += [f"  BUFx2_ASAP7_75t_R o_{i} (.A(l[{i}]), .Y(y[{i}]));",
                  f"  DFFHQNx1_ASAP7_75t_R \\r1[{i}]$_DFF_P_ (.CLK(clk), .D(q0[{i}]), .QN(yn[{i}]));"]
        else:
            s += [f"  DFFHQNx1_ASAP7_75t_R \\r1[{i}]$_DFF_P_ (.CLK(clk), .D(l[{i}]), .QN(yn[{i}]));",
                  f"  INVx1_ASAP7_75t_R i1_{i} (.A(yn[{i}]), .Y(y[{i}]));"]
    s += ["  DFFHQNx1_ASAP7_75t_R \\n0$_DFF_P_ (.CLK(clk), .D(b), .QN(n0n));",
          "  INVx1_ASAP7_75t_R in0 (.A(n0n), .Y(n0));"]
    if v == "NEG":                     # a latch into the falling-edge flop
        s += ["  DLLx1_ASAP7_75t_R lkn (.CLK(clk), .D(n0), .Q(ln));"]
    else:
        s += ["  BUFx2_ASAP7_75t_R bn (.A(n0), .Y(ln));"]
    s += ["  DFFLQNx1_ASAP7_75t_R \\n1$_DFF_N_ (.CLK(clk), .D(ln), .QN(n1n));",
          "  INVx1_ASAP7_75t_R in1 (.A(n1n), .Y(z));", "endmodule", ""]
    return "\n".join(s)


def _kit(tmp_path, v):
    k = tmp_path / v
    (k / "rtl").mkdir(parents=True)
    (k / "rtl" / "lec_lk_t.sv").write_text(RTL)
    n = k / "run" / "results" / "asap7" / "lec_lk_t" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(_netlist(v))
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_lk_t\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/rtl/lec_lk_t.sv\n"
        "export VERILOG_INCLUDE_DIRS = /work/rtl\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\n")
    return k


def _run(kit, **env):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900, env=dict(os.environ, **env))
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


def test_lockup_cells():
    assert lec.LOCKUP_CELLS.match("DLLx1_ASAP7_75t_R") and lec.LOCKUP_CELLS.match("DLLx3_ASAP7_75t_SL")
    assert not lec.LOCKUP_CELLS.match("DHLx1_ASAP7_75t_R") and lec.UNSUPPORTED_CELLS.match("DHLx1_ASAP7_75t_R")


@needs_image
def test_lockup_latch_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["lockup_latches"]["gate"]["to_wire"] == 2 and r["lockup_latches"]["gold"]["latches"] == 0, r


@needs_image
@pytest.mark.parametrize("mut", ["MUT_SKIP", "MUT_DROP"])
def test_lockup_mutants_are_not_equivalent(tmp_path, mut):
    rc, r = _run(_kit(tmp_path, mut))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r


@needs_image
@pytest.mark.parametrize("ref,why", [("DHL", "does not model"), ("INV", "transparent-low"),
                                     ("DATACLK", "transparent-low"), ("NEG", "Q reaches"),
                                     ("PO", "lec_po_y")])
def test_latch_topologies_outside_the_model_are_refused(tmp_path, ref, why):
    rc, r = _run(_kit(tmp_path, ref))
    assert rc == 2 and r["verdict"] == "UNPROVEN" and why in r["reason"], r


@needs_image
def test_latch_switch_off_refuses(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"), OT_LEC_LATCH="0")
    assert rc == 2 and r["verdict"] == "UNPROVEN" and "does not model" in r["reason"], r
