"""Recipe-2 pin hooks in the real tools (el1014-root-recipe2, 2026-10-14).

OpenROAD: physical/common_flow/pin_reg_split.tcl gives every flop-driven output its own launch flop (a merged flop on an
INV fanout, a pin flop that also feeds internal logic), then leaf_iohold.tcl pads with HB2 (HB4 only on the
OT_HOLD_PAD_STRONG_RE ports) and io_flop_at_pins.tcl anchors every launch flop FIRM at its pin.
Yosys: physical/common_flow/ot_keep_regs.tcl with OT_KEEP_PIN_REGS=1 keeps equal top-level pin registers apart.
Skipped when docker or the ORFS image is not available (the gate host has both).
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMAGE = "openroad/orfs:latest"
OR = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
YS = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"

NETLIST = """
module top(clk, d, e, ia, o0, o1, o2, o3, o4, o5, oi);
  input clk; input d; input e; input ia;
  output o0, o1, o2, o3, o4, o5, oi;
  wire qn0, q0, qn1, qn2, x;
  DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(d), .QN(qn0));   // merged pin register: INV fanout 3 -> o0 o1 o2
  INVx1_ASAP7_75t_R i0 (.A(qn0), .Y(q0));
  BUFx2_ASAP7_75t_R b0 (.A(q0), .Y(o0));
  BUFx2_ASAP7_75t_R b1 (.A(q0), .Y(o1));
  BUFx2_ASAP7_75t_R b2 (.A(q0), .Y(o2));
  DFFHQNx1_ASAP7_75t_R f1 (.CLK(clk), .D(e), .QN(qn1));   // pin register that also feeds internal logic
  INVx1_ASAP7_75t_R i1 (.A(qn1), .Y(o3));
  NAND2xp5_ASAP7_75t_R n1 (.A(qn1), .B(e), .Y(x));
  DFFHQNx1_ASAP7_75t_R f3 (.CLK(clk), .D(x), .QN(oi));
  DFFHQNx1_ASAP7_75t_R f2 (.CLK(clk), .D(ia), .QN(qn2));  // already dedicated
  INVx1_ASAP7_75t_R i2 (.A(qn2), .Y(o4));
  NAND2xp5_ASAP7_75t_R n2 (.A(d), .B(e), .Y(o5));          // not flop-driven
endmodule
"""

FLOW = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] { read_liberty $l }
read_verilog /w/t.v
link_design top
initialize_floorplan -die_area {0 0 40 40} -core_area {2 2 38 38} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
set ::env(RESULTS_DIR) /tmp/res
file mkdir /tmp/res
set ::env(OT_INHOLD_MASTER) HB2xp67_ASAP7_75t_R
set ::env(OT_INHOLD_DRV) BUFx4f_ASAP7_75t_R
set ::env(OT_HOLD_PAD_STRONG_RE) {^o3$}
set ::env(OT_IOHOLD_IN) 1
set ::env(OT_OFLOP_HOPS) 8
set ::env(OT_OFLOP_ALLOW_NONE) 1
source /src/physical/common_flow/pin_reg_split.tcl
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
set blk [ord::get_db_block]
foreach b [$blk getBTerms] {
  if {[$b getIoType] ne "OUTPUT"} continue
  set cn [$b getNet]; set path {}
  for {set i 0} {$i < 8} {incr i} {
    set dv ""; foreach it [$cn getITerms] { if {[$it isOutputSignal]} { set dv $it } }
    if {$dv eq ""} break
    set inst [$dv getInst]
    set loads 0; foreach it [$cn getITerms] { if {[$it isInputSignal]} { incr loads } }
    lappend path "[[$inst getMaster] getName]/L$loads/B[llength [$cn getBTerms]]/[$inst getPlacementStatus]"
    if {[string match DFF* [[$inst getMaster] getName]]} break
    set a [$inst findITerm A]; if {$a eq "NULL"} break
    set cn [$a getNet]
  }
  puts "PATH [$b getName] [join $path { }]"
}
"""


def docker_ok():
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    return r.returncode == 0


@unittest.skipUnless(docker_ok(), "docker + ORFS image needed")
class PinRegSplit(unittest.TestCase):
    def run_or(self):
        with tempfile.TemporaryDirectory() as w:
            (Path(w) / "t.v").write_text(NETLIST)
            (Path(w) / "run.tcl").write_text(FLOW)
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{w}:/w", "-v", f"{ROOT}:/src:ro", IMAGE, OR, "-no_init",
                                "-exit", "/w/run.tcl"], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
        return r.stdout

    def test_one_dedicated_anchored_flop_per_output(self):
        out = self.run_or()
        self.assertIn("OT_PRS: 3 output pins already on a dedicated flop, 3 pins split onto a cloned flop", out)
        paths = {ln.split()[1]: ln.split()[2:] for ln in out.splitlines() if ln.startswith("PATH ")}
        for p in ("o0", "o1", "o2", "o3", "o4", "oi"):
            chain = paths[p]
            self.assertTrue(chain[-1].startswith("DFF"), (p, chain))
            # every net from the flop to the port has ONE consumer, and the flop is FIRM at its pin
            for hop in chain[:-1]:
                self.assertRegex(hop, r"/L[01]/B[01]/", (p, chain))
            self.assertIn("/L1/B0/FIRM", chain[-1], (p, chain))
        # pad: HB2 everywhere, HB4 only on the strong-pad port
        self.assertTrue(any(h.startswith("HB4xp67") for h in paths["o3"]), paths["o3"])
        for p in ("o0", "o1", "o2", "o4", "oi"):
            self.assertTrue(any(h.startswith("HB2xp67") for h in paths[p]), (p, paths[p]))
            self.assertFalse(any(h.startswith("HB4xp67") for h in paths[p]), (p, paths[p]))
        self.assertTrue(paths["o5"][0].startswith("HB2") or paths["o5"][0].startswith("NAND2"), paths["o5"])


KEEP_RTL = """
module sub(input clk, input [3:0] d, output reg [3:0] q);
  always @(posedge clk) q <= d;
endmodule
module top(input clk, input [3:0] a, output [3:0] o1, output [3:0] o2, output [3:0] o3, output [3:0] o4);
  reg [3:0] r1, r2;
  always @(posedge clk) begin r1 <= a; r2 <= a; end
  assign o1 = r1;
  assign o2 = r2;
  assign o3 = ~r1;
  sub u0(.clk(clk), .d(a), .q(o4));
endmodule
"""


@unittest.skipUnless(docker_ok(), "docker + ORFS image needed")
class KeepPinRegs(unittest.TestCase):
    def flops(self, on):
        with tempfile.TemporaryDirectory() as w:
            (Path(w) / "t.v").write_text(KEEP_RTL)
            (Path(w) / "run.tcl").write_text(
                "yosys read_verilog /w/t.v\nyosys hierarchy -check -top top\nset ::env(DESIGN_NAME) top\n"
                f"set ::env(OT_KEEP_PIN_REGS) {on}\nsource /src/physical/common_flow/ot_keep_regs.tcl\n"
                "yosys synth -flatten -top top\nyosys tee -o /w/stat.txt stat\n")
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{w}:/w", "-v", f"{ROOT}:/src:ro", IMAGE, YS, "-q", "-c",
                                "/w/run.tcl"], capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            st = (Path(w) / "stat.txt").read_text()
        return sum(int(ln.split()[0]) for ln in st.splitlines() if "_DFF_" in ln)

    def test_equal_top_level_pin_registers_stay_apart(self):
        self.assertEqual(self.flops(0), 4)        # opt_merge folds r1 / r2 / u0.q (equal D) into one 4-bit register
        self.assertEqual(self.flops(1), 8)        # r1 and r2 kept; u0.q (submodule) is split by pin_reg_split.tcl


if __name__ == "__main__":
    unittest.main()
