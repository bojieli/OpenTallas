"""Run the official corner helper against a post-SDC that overwrites `c`."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class CornerScope(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tclsh"), "requires Tcl")
    def test_post_sdc_cannot_change_scene_or_skip_setup_protection(self):
        for corner in ("ss", "ff"):
            with self.subTest(corner=corner), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                (root / "post.sdc").write_text("set c overwritten_clock_pointer\n")
                fixture = r'''
foreach cmd {read_lef read_liberty read_db set_propagated_clock} {
    proc $cmd {args} {}
}
foreach cmd {all_clocks get_pins all_registers all_outputs find_timing_paths} {
    proc $cmd {args} {return {}}
}
proc read_sdc {path} {uplevel #0 [list source $path]}
proc write_sdc {args} {set f [open [lindex $args end] w]; close $f}
namespace eval sta {
    proc worst_slack_cmd {args} {return 1e-11}
    proc total_negative_slack_cmd {args} {return 0}
}
set ::env(OT_CORNER) [lindex $argv 0]
set ::env(OT_SETUP_LIB) TT
set ::env(OT_DB) unused
set ::env(OT_SDC) [lindex $argv 1]
set ::env(OT_POST_SDC) [lindex $argv 1]
set ::env(OT_EFF) [lindex $argv 2]
source [lindex $argv 3]
'''
                (root / "fixture.tcl").write_text(fixture)
                eff = root / "effective.sdc"
                result = subprocess.run(["tclsh", str(root / "fixture.tcl"),
                    corner, str(root / "post.sdc"), str(eff),
                    str(HERE / "hold_eco_corner.tcl")], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"OT_CORNER_EFF {corner} ws_max", result.stdout)
                self.assertNotIn("overwritten_clock_pointer", result.stdout)
                self.assertTrue(eff.exists())
                self.assertEqual(pathlib.Path(str(eff) + ".slack").exists(), corner == "ss")
                self.assertEqual(pathlib.Path(str(eff) + ".crit").exists(), corner == "ss")


if __name__ == "__main__":
    unittest.main()
