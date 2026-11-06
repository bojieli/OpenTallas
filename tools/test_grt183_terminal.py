"""Exercise the actual Tcl error wrapper without a physical-design process."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / "physical/common_flow/grt183_resume.tcl"

class TerminalCaptureTest(unittest.TestCase):
    def run_hook(self, recovered=True, writer_fails=False, message="GRT-0183 quoted \"error\"\nnext\\line"):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            if recovered:
                (root/"5_1_grt.grt183_recovered.json").write_text("{}")
            script = r"""
namespace eval ord {proc get_db_block {} {return block}}
proc block {args} {return {}}
proc repair_design_helper {args} {
    return -code error -errorcode {GRT ORIGINAL 183} $::test_message
}
proc write_db {path} {
    incr ::writes
    if {$::writer_fails} {error "disk writer rejected"}
    set f [open $path w]; puts $f "actual terminal shapes intact"; close $f
}
set ::writes 0
set ::env(RESULTS_DIR) [lindex $argv 0]
set ::writer_fails [lindex $argv 1]
set ::test_message [lindex $argv 2]
source [lindex $argv 3]
rename ot_g183::strip_hook_shapes ot_g183::original_strip
proc ot_g183::strip_hook_shapes {} {
    incr ::strips
    return 7
}
set ::strips 0
set rc [catch {repair_design_helper keep_original_args} msg opts]
if {$rc != 1 || $msg ne $::test_message || [dict get $opts -errorcode] ne {GRT ORIGINAL 183}} {
    error "original failure/options changed: $rc $msg $opts"
}
puts "RESULT $::writes $::strips"
"""
            probe = root/"probe.tcl"
            probe.write_text(script)
            run = subprocess.run(["tclsh", str(probe), d, str(int(writer_fails)), message, str(HOOK)],
                                 capture_output=True, text=True, check=True)
            captures = [json.loads(p.read_text()) for p in root.glob("*.grt183_terminal.*.json")]
            snapshots = [p.read_text() for p in root.glob("*.odb")]
            return run.stdout, captures, snapshots

    def test_terminal_saves_actual_geometry_and_original_error(self):
        out, rows, snapshots = self.run_hook()
        self.assertIn("RESULT 1 0", out)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["helper"], "repair_design_helper")
        self.assertEqual(rows[0]["db_status"], "SAVED")
        self.assertEqual(rows[0]["scope"], "DIAGNOSTIC_ONLY_NO_RETRY")
        self.assertEqual(rows[0]["error"], 'GRT-0183 quoted "error"\nnext\\line')
        self.assertEqual(snapshots, ["actual terminal shapes intact\n"])
        self.assertIn("OT_GRT183_RESUME_REFUSED", out)

    def test_failed_snapshot_keeps_original_failure_and_metadata(self):
        out, rows, snapshots = self.run_hook(writer_fails=True)
        self.assertIn("RESULT 1 0", out)
        self.assertEqual(rows[0]["db_status"], "WRITE_FAILED")
        self.assertEqual(rows[0]["db_detail"], "disk writer rejected")
        self.assertFalse(snapshots)

    def test_first_resume_behavior_stays_unchanged(self):
        out, rows, snapshots = self.run_hook(recovered=False)
        self.assertIn("RESULT 1 1", out)
        self.assertIn("OT_GRT183_RESUME_SAVED", out)
        self.assertFalse(rows)
        self.assertEqual(len(snapshots), 1)

    def test_unrelated_error_does_not_snapshot(self):
        out, rows, snapshots = self.run_hook(message="GRT-9999 unrelated")
        self.assertIn("RESULT 0 0", out)
        self.assertFalse(rows)
        self.assertFalse(snapshots)

if __name__ == "__main__":
    unittest.main()
