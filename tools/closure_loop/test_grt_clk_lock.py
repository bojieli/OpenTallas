"""GRT-CLK-LOCK (FLOW-CLOCK-R8 2026-10-29): in the GRT stage of a two-mode session every clock-net instance is FIRM
while detailed_placement legalizes the repair's buffers, so global_route -end_incremental does not re-route clock nets
after the hold repair timed them (HBM qwdec_k22pad_m10: repair FF hold +4.39 -> pre-route gate -6.16 on the written
5_1_grt.odb; 636 clock-net instances moved, 333 / 1788 clock nets re-routed).  Runs under tclsh against a mock odb."""
import shutil
import subprocess
import unittest

import closure_loop as cl

TCL = cl.HERE.parent / "orfs_hold_mm.tcl"

MOCK = r"""
# insts: name -> status ; nets: name -> {sigtype {inst ...}}
array set ::st {ck_buf PLACED ff1 PLACED ff2 PLACED locked_buf LOCKED data1 PLACED hb1 PLACED}
set ::nets {clknet {CLOCK {ck_buf ff1 ff2 locked_buf}} n1 {SIGNAL {ff1 data1 hb1}}}
proc mkinst {n} { proc ::inst_$n {m args} [string map [list @N@ $n] {
  switch $m { getName { return @N@ } getPlacementStatus { return $::st(@N@) } setPlacementStatus { set ::st(@N@) [lindex $args 0] } }
}]; return ::inst_$n }
proc mkiterm {n} { proc ::it_$n {m} [string map [list @N@ $n] { return [mkinst @N@] }]; return ::it_$n }
proc mknet {name} { proc ::net_$name {m} [string map [list @N@ $name] {
  lassign [dict get $::nets @N@] t insts
  switch $m { getSigType { return $t } getITerms { return [lmap i $insts {mkiterm $i}] } }
}]; return ::net_$name }
namespace eval ord { proc get_db_block {} { return ::mockblock } }
proc ::mockblock {m} { return [lmap n [dict keys $::nets] {mknet $n}] }
proc detailed_placement {args} {
  set ::during [lsort [lmap n [array names ::st] {list $n $::st($n)}]]
  if {[info exists ::dpl_fail]} { error "DPL-0036 mock failure" }
  return ok
}
"""


def run(stage, env=None, fail=False, twice=False):
    src = TCL.read_text()
    block = src[src.index("# BEGIN GRT-CLK-LOCK"):src.index("# END GRT-CLK-LOCK")]
    pre = "".join(f"set ::env({k}) {v}\n" for k, v in (env or {}).items())
    if stage:
        pre += f"set ::ot_mm_stage {stage}\n"
    if fail:
        pre += "set ::dpl_fail 1\n"
    body = block + ("\n" + block if twice else "")
    script = (MOCK + pre + body +
              "\nset rc [catch {detailed_placement -max_displacement 10} msg]\nputs \"RC $rc $msg\"\n"
              "puts \"DURING $::during\"\nputs \"AFTER [lsort [lmap n [array names ::st] {list $n $::st($n)}]]\"\n")
    r = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True)
    out = {ln.split(" ", 1)[0]: ln.split(" ", 1)[1] for ln in r.stdout.splitlines() if " " in ln}
    return r.stdout, out


AFTER = "{ck_buf PLACED} {data1 PLACED} {ff1 PLACED} {ff2 PLACED} {hb1 PLACED} {locked_buf LOCKED}"


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class GrtClkLockTests(unittest.TestCase):
    def test_grt_stage_locks_clock_insts_during_dpl_and_restores(self):
        log, o = run("4_cts.sdc")
        self.assertEqual(o["DURING"], "{ck_buf FIRM} {data1 PLACED} {ff1 FIRM} {ff2 FIRM} {hb1 PLACED} {locked_buf LOCKED}")
        self.assertEqual(o["AFTER"], AFTER)
        self.assertIn("OT_GRT_CLK_LOCK: 3 clock-net instances FIRM", log)
        self.assertTrue(o["RC"].startswith("0 ok"))

    def test_cts_stage_and_non_mm_untouched(self):
        for stage in ("3_place.sdc", None):
            log, o = run(stage)
            self.assertEqual(o["DURING"], AFTER)
            self.assertNotIn("OT_GRT_CLK_LOCK", log)

    def test_opt_out(self):
        _, o = run("4_cts.sdc", env={"OT_GRT_CLK_LOCK": 0})
        self.assertEqual(o["DURING"], AFTER)

    def test_restores_on_dpl_error_and_is_idempotent_when_sourced_twice(self):
        _, o = run("4_cts.sdc", fail=True, twice=True)
        self.assertTrue(o["RC"].startswith("1 DPL-0036"))
        self.assertEqual(o["AFTER"], AFTER)
        self.assertIn("{ff1 FIRM}", o["DURING"])


if __name__ == "__main__":
    unittest.main()
