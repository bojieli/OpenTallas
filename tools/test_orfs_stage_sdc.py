"""MM-STAGE-SDC (FLOW-9 10-30): a stage SDC written while an FF mode is synced must not carry the ss hold false path."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from orfs_hold_mm import WSDC_BLOCK, WSDC_WRITE, patch_stage_sdc

UTIL = ("proc orfs_write_db { output_file } {\n  log_cmd write_db $output_file\n}\n\n"
        "proc orfs_write_sdc { output_file } {\n  if { !$::env(WRITE_ODB_AND_SDC_EACH_STAGE) } {\n    return\n  }\n"
        + WSDC_WRITE + "}\n\nproc other {} {}\n")
# Stub session with the orfs_hold_mm semantics that matter here: sync adds the mode-ss hold false path and sets
# ::ot_mm_synced; unsync removes it; write_sdc dumps the current exceptions.
STUB = r"""
set ::env(WRITE_ODB_AND_SDC_EACH_STAGE) 1
set ::exc {}
proc log_cmd {args} { {*}$args }
proc write_sdc {-no_timestamp f} { set h [open $f w]; puts $h [join $::exc \n]; close $h }
proc ot_mm_sync {} { lappend ::exc "set_false_path -hold -from \[all_clocks\]"; set ::ot_mm_synced 1; incr ::syncs }
proc ot_mm_unsync {} {
  if {![info exists ::ot_mm_synced]} { return }
  set ::exc [lsearch -all -inline -not -exact $::exc "set_false_path -hold -from \[all_clocks\]"]; unset ::ot_mm_synced
}
set ::syncs 0
source [lindex $argv 0]
set d [lindex $argv 1]
orfs_write_sdc $d/plain.sdc
ot_mm_sync
orfs_write_sdc $d/synced.sdc
puts "synced_after=[info exists ::ot_mm_synced] syncs=$::syncs exc=[llength $::exc]"
"""


class StageSdcPatchTest(unittest.TestCase):
    def fixture(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name)
        (path / "util.tcl").write_text(text)
        return path

    def test_patch_is_idempotent_and_local(self):
        path = self.fixture(UTIL)
        self.assertEqual(patch_stage_sdc(path), "patched")
        out = (path / "util.tcl").read_text()
        self.assertEqual(out, UTIL.replace(WSDC_WRITE, WSDC_BLOCK, 1))
        self.assertEqual(patch_stage_sdc(path), "already patched")
        self.assertEqual(out, (path / "util.tcl").read_text())

    def test_unknown_text_refused_without_write(self):
        for text in ["unknown\n", UTIL.replace(WSDC_WRITE, ""), UTIL + "\n" + WSDC_WRITE,
                     UTIL.replace("proc orfs_write_sdc", "proc orfs_write_sdc2"), "# ot_mm_resync\n" + UTIL]:
            with self.subTest(text=text):
                path = self.fixture(text)
                with self.assertRaises(SystemExit):
                    patch_stage_sdc(path)
                self.assertEqual((path / "util.tcl").read_text(), text)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh not installed")
    def test_synced_session_writes_route_sdc_and_stays_synced(self):
        path = self.fixture(UTIL)
        patch_stage_sdc(path)
        (path / "stub.tcl").write_text(STUB)
        r = subprocess.run(["tclsh", str(path / "stub.tcl"), str(path / "util.tcl"), str(path)],
                           capture_output=True, text=True, check=True)
        self.assertIn("synced_after=1 syncs=2 exc=1", r.stdout)
        self.assertNotIn("false_path", (path / "synced.sdc").read_text())
        self.assertNotIn("false_path", (path / "plain.sdc").read_text())
        self.assertIn("OT_HOLD_MM: stage SDC", r.stdout)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh not installed")
    def test_unpatched_flow_leaks_the_hold_false_path(self):
        path = self.fixture(UTIL)
        (path / "stub.tcl").write_text(STUB)
        subprocess.run(["tclsh", str(path / "stub.tcl"), str(path / "util.tcl"), str(path)],
                       capture_output=True, text=True, check=True)
        self.assertIn("set_false_path -hold", (path / "synced.sdc").read_text())


if __name__ == "__main__":
    unittest.main()
