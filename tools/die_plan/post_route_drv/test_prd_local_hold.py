"""KW-FIX-23 (COORD 12:0x): prd_local_branches holds flops FIRM only (no dont_touch -> no RSZ-3006);
the sequential audit still fails on any flop master/location/orient change and restores the old status."""
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
STUB = r'''
namespace eval ord {proc get_db_block {} {return blk}}
proc blk {m args} {switch $m {getInsts {return {ff buf}} findInst {return [lindex $args 0]}}}
array set st {ff PLACED buf PLACED}; array set dt {ff 0 buf 0}; array set ms {ff DFFHQNx1_ASAP7_75t_R buf BUFx2_ASAP7_75t_R}
foreach n {ff buf} {
 proc $n {m args} [string map [list @N@ $n] {
  switch $m {
   getMaster {return m_@N@} getName {return @N@} getLocation {return {10 20}} getOrient {return R0}
   getPlacementStatus {return $::st(@N@)} setPlacementStatus {set ::st(@N@) [lindex $args 0]}
   isDoNotTouch {return $::dt(@N@)} setDoNotTouch {set ::dt(@N@) [lindex $args 0]}
  }}]
 proc m_$n {m args} [string map [list @N@ $n] {
  switch $m {getMTerms {return {}} getName {return $::ms(@N@)} isBlock {return 0}}}]
}
source [lindex $argv 0]
ot_prd_local_hold_sequential
puts "HELD $::st(ff) $::dt(ff) $::st(buf) $::dt(buf)"
if {[lindex $argv 1] eq "resize"} {set ::ms(ff) DFFHQNx2_ASAP7_75t_R}
if {[catch {ot_prd_local_sequential_audit} e]} {puts "AUDIT_ERR $e"} else {puts "AFTER $::st(ff) $::dt(ff)"}
'''


class Hold(unittest.TestCase):
    def run_tcl(self, mode):
        with tempfile.TemporaryDirectory() as d:
            s = pathlib.Path(d) / "stub.tcl"
            s.write_text(STUB)
            r = subprocess.run(["tclsh", str(s), str(HERE / "prd_local_branches.tcl"), mode],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout

    def test_flops_firm_not_dont_touch(self):
        out = self.run_tcl("keep")
        self.assertIn("HELD FIRM 0 PLACED 0", out)
        self.assertIn("AFTER PLACED 0", out)

    def test_audit_fails_on_flop_change(self):
        self.assertIn("AUDIT_ERR OT_PRD_LOCAL_BRANCH sequential pose/master changed: ff", self.run_tcl("resize"))


if __name__ == "__main__":
    unittest.main()
