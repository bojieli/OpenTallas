"""Clock spine + OT_SPINE_CTS_REST=1 in the real OpenROAD (el1014-root-macro-edge, 2026-10-14).

physical/common_flow/clock_spine.tcl builds the spine of OT_SPINE_PORT (FIRM + dont_touch buffers); with
OT_SPINE_CTS_REST=1 TritonCTS must then build only the OTHER clocks.  Called with the flow's own arguments (no -clk_nets)
TritonCTS rediscovered the spine clock, re-clustered its multi-sink spine nets and died on ODB-0370 (disconnect term A of
a dont_touch spine buffer: qfd_coll_xfifo_native n13 --cts gate).  This test places a two-clock block (ck: 16 flops,
ckd: 256 flops over 160 x 160 um), runs the ORFS CTS command line through the wrapper and checks that CTS completes, that
TritonCTS was given only ck, that every spine buffer and spine net is unchanged and that ck got a tree.
OT_SPINE_TEST_MUTANT=1 re-runs with the pre-fix wrapper call (all clocks) and expects the ODB-0370 failure.
Skipped when docker or the ORFS image is not available.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMAGE = "openroad/orfs:latest"
OR = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
N_CK, N_CKD = 16, 256


def netlist():
    cells = [f"  DFFHQNx1_ASAP7_75t_R a{i} (.CLK(ck), .D(d), .QN(qa[{i}]));" for i in range(N_CK)]
    cells += [f"  DFFHQNx1_ASAP7_75t_R b{i} (.CLK(ckd), .D(d), .QN(qb[{i}]));" for i in range(N_CKD)]
    return ("module top(ck, ckd, d, y, z);\n  input ck, ckd, d; output y, z;\n"
            f"  wire [{N_CK - 1}:0] qa; wire [{N_CKD - 1}:0] qb;\n" + "\n".join(cells) +
            "\n  assign y = qa[0];\n  assign z = qb[0];\nendmodule\n")


FLOW = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] { read_liberty $l }
read_verilog /w/t.v
link_design top
initialize_floorplan -die_area {0 0 180 180} -core_area {5.4 5.4 174.6 174.6} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
create_clock -name core_clk -period 500 [get_ports ck]
create_clock -name ckd -period 500 [get_ports ckd]
source $P/setRC.tcl
set u [[ord::get_db_block] getDbUnitsPerMicron]
set k 0
foreach i [[ord::get_db_block] getInsts] {
  set n [$i getName]
  if {[string match a* $n]} { set x [expr {20 + 8 * ($k %% 16)}]; set y 90 } else {
    set j [expr {$k - 16}]; set x [expr {12 + 9.5 * ($j %% 16)}]; set y [expr {12 + 9.5 * ($j / 16)}]
  }
  $i setLocation [expr {int($x * $u)}] [expr {int($y * $u)}]; $i setPlacementStatus PLACED
  incr k
}
detailed_placement
set ::env(OT_SPINE_PORT) ckd
set ::env(OT_SPINE_CTS_REST) 1
set ::env(OT_SPINE_ITERS) 1
set ::env(OT_SPINE_BIN) 30
source /src/physical/common_flow/clock_spine.tcl
%(mutant)s
clock_tree_synthesis -sink_clustering_enable -repair_clock_nets -buf_list BUFx4_ASAP7_75t_R -root_buf BUFx4_ASAP7_75t_R
set sp 0; set spdt 0
foreach i [[ord::get_db_block] getInsts] {
  if {[string match clkbuf_sp_* [$i getName]]} { incr sp; if {[$i isDoNotTouch] && [$i getPlacementStatus] eq "FIRM"} { incr spdt } }
}
set ckn [[[ord::get_db_block] findBTerm ck] getNet]
puts "RESULT spine $sp dont_touch_firm $spdt ck_root_fanout [llength [$ckn getITerms]]"
"""

MUTANT = r"""
rename clock_tree_synthesis ot_fixed_cts
proc clock_tree_synthesis {args} { ot_clock_spine; return [ot_spine_cts_orig {*}$args] }
"""


def docker_ok():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


@unittest.skipUnless(docker_ok(), "docker + ORFS image needed")
class SpineCtsRest(unittest.TestCase):
    def run_or(self, mutant=False):
        with tempfile.TemporaryDirectory() as w:
            os.chmod(w, 0o777)
            (Path(w) / "t.v").write_text(netlist())
            (Path(w) / "run.tcl").write_text(FLOW % {"mutant": MUTANT if mutant else ""})
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{w}:/w", "-v", f"{ROOT}:/src:ro", IMAGE, OR, "-no_init",
                                "-exit", "/w/run.tcl"], capture_output=True, text=True, timeout=900)
        return r.returncode, r.stdout + r.stderr

    def test_rest_pass_builds_only_other_clocks(self):
        rc, out = self.run_or()
        self.assertEqual(rc, 0, out[-4000:])
        self.assertIn("OT_SPINE done port ckd", out)
        self.assertIn("OT_SPINE rest: TritonCTS on -clk_nets {ck}", out)
        self.assertNotIn("ODB-0370", out)
        self.assertNotRegex(out, r'CTS-0010\]\s+Clock net "clkbuf_sp_')      # TritonCTS never saw a spine net
        m = re.search(r"RESULT spine (\d+) dont_touch_firm (\d+) ck_root_fanout (\d+)", out)
        self.assertIsNotNone(m, out[-3000:])
        self.assertGreater(int(m.group(1)), 0)
        self.assertEqual(m.group(1), m.group(2))
        self.assertLess(int(m.group(3)), N_CK)                               # ck got a tree (root no longer drives every flop)

    def test_mutant_all_clocks_rediscovers_spine(self):
        rc, out = self.run_or(mutant=True)
        self.assertRegex(out, r'CTS-0010\]\s+Clock net "clkbuf_sp_', out[-3000:])
        self.assertNotEqual(rc, 0)
        self.assertRegex(out, r"ODB-0370\] Attempt to disconnect term A of dont_touch instance clkbuf_sp_")


if __name__ == "__main__":
    unittest.main()
