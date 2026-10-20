"""Standard-mode PG binding before protection in the real OpenROAD (ROOT4-PGFLOW, 2026-10-19).

OpenROAD global_connect skips dont_touch instances (dbGlobalConnect.cpp:163). The default (non-strict) protection
hooks set dont_touch on CTS-inserted buffers BEFORE the final global_connect, so their VDD/VSS terminals stayed
unbound (S81 STA.PG: sysface 18.9k, sf7w 32.3k unbound). physical/common_flow/clk_net_protect.tcl now runs
ot_pg_standard_bind (the design's own global_connect rules) before protecting.

The block below: a placed flop netlist, PG nets + global-connect rules + one global_connect (as the PDN stage does),
then a CTS-like clkbuf_* buffer is created on a CLOCK net (unbound PG, as TritonCTS leaves it), the protection hook
runs, then the final global_connect. Checks: every native PG terminal is bound and the buffer is dont_touch.
Mutant (OLD ordering, ot_pg_standard_bind replaced by a no-op): the buffer's PG terminals stay unbound -> FAIL.
Also checks that standard mode adds no strict-mode refusal (no OT_PG_*_REFUSED). Skipped without docker/ORFS image.
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

NETLIST = """module top(ck, d, y);
  input ck, d; output y; wire [3:0] q;
  DFFHQNx1_ASAP7_75t_R a0 (.CLK(ck), .D(d), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R a1 (.CLK(ck), .D(q[0]), .QN(q[1]));
  DFFHQNx1_ASAP7_75t_R a2 (.CLK(ck), .D(q[1]), .QN(q[2]));
  DFFHQNx1_ASAP7_75t_R a3 (.CLK(ck), .D(q[2]), .QN(q[3]));
  assign y = q[3];
endmodule
"""

FLOW = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] { read_liberty $l }
read_verilog /w/t.v
link_design top
initialize_floorplan -die_area {0 0 40 40} -core_area {5.4 5.4 34.56 34.56} -site asap7sc7p5t
create_clock -name core_clk -period 500 [get_ports ck]
set blk [ord::get_db_block]
foreach {n t} {VDD POWER VSS GROUND} { set pn [odb::dbNet_create $blk $n]; $pn setSpecial; $pn setSigType $t }
add_global_connection -net VDD -pin_pattern {^VDD$} -power
add_global_connection -net VSS -pin_pattern {^VSS$} -ground
global_connect
# CTS-like insertion after the PDN global_connect: clkbuf_0 drives the flops' clock net.
set ckn [[$blk findBTerm ck] getNet]
$ckn setSigType CLOCK
set b [odb::dbInst_create $blk [[ord::get_db] findMaster BUFx4_ASAP7_75t_R] clkbuf_0]
$b setLocation 10000 10000; $b setPlacementStatus PLACED
set nn [odb::dbNet_create $blk clknet_0]; $nn setSigType CLOCK
foreach it [$ckn getITerms] { if {[[$it getInst] getName] ne "clkbuf_0"} { $it disconnect; $it connect $nn } }
[$b findITerm A] connect $ckn
[$b findITerm Y] connect $nn
source /src/physical/common_flow/clk_net_protect.tcl
%(mutant)s
ot_protect_clock_tree
global_connect
set unb 0; set tot 0
foreach i [$blk getInsts] {
  foreach it [$i getITerms] {
    if {[[$it getMTerm] getSigType] ni {POWER GROUND}} continue
    incr tot
    if {[$it getNet] eq "NULL"} { incr unb; puts "UNBOUND [$i getName]/[[$it getMTerm] getName]" }
  }
}
puts "RESULT pg_total $tot pg_unbound $unb clkbuf_dont_touch [$b isDoNotTouch]"
"""

MUTANT = "proc ot_pg_standard_bind {where} { return 0 }"


def docker_ok():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


@unittest.skipUnless(docker_ok(), "docker + ORFS image needed")
class PgStandardBind(unittest.TestCase):
    def run_or(self, mutant=False):
        with tempfile.TemporaryDirectory() as w:
            os.chmod(w, 0o777)
            (Path(w) / "t.v").write_text(NETLIST)
            (Path(w) / "run.tcl").write_text(FLOW % {"mutant": MUTANT if mutant else ""})
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{w}:/w", "-v", f"{ROOT}:/src:ro", IMAGE, OR,
                                "-no_init", "-exit", "/w/run.tcl"], capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        m = re.search(r"RESULT pg_total (\d+) pg_unbound (\d+) clkbuf_dont_touch (\d)", out)
        self.assertIsNotNone(m, out[-3000:])
        return r.returncode, out, int(m.group(1)), int(m.group(2)), int(m.group(3))

    def test_standard_mode_binds_before_protect(self):
        rc, out, tot, unb, dt = self.run_or()
        self.assertEqual(rc, 0, out[-3000:])
        self.assertIn("OT_PG_STANDARD_BIND protect_clock_tree rules=2", out)
        self.assertNotRegex(out, r"OT_PG_\w*REFUSED")
        self.assertGreaterEqual(tot, 10)                 # 4 flops + clkbuf, VDD+VSS each
        self.assertEqual(unb, 0, out[-3000:])
        self.assertEqual(dt, 1)

    def test_mutant_old_ordering_leaves_clkbuf_unbound(self):
        rc, out, tot, unb, dt = self.run_or(mutant=True)
        self.assertEqual(dt, 1)
        self.assertGreater(unb, 0, out[-3000:])
        self.assertIn("UNBOUND clkbuf_0/", out)


if __name__ == "__main__":
    unittest.main()
