"""RSZ-3006 class (QC fw 11-11): grt183_resume.tcl sets dont_touch on nets feeding dont_touch u_hdly_ pad loads before
repair_timing, so the in-flow hold repair does not die on 'Load pin ... is dont_touch'."""
import shutil
import subprocess
import unittest
from pathlib import Path

TCL = Path(__file__).resolve().parents[2] / "physical" / "common_flow" / "grt183_resume.tcl"


class PadNetsDnt(unittest.TestCase):
    def test_hook_present_and_scoped(self):
        s = TCL.read_text()
        self.assertIn("proc protect_pad_nets", s)
        self.assertIn('"u_hdly_"', s)
        self.assertIn("isDoNotTouch", s)
        self.assertIn('"@H@" eq "repair_timing_helper"', s)
        self.assertIn("OT_HB4_PAD_NETS_DNT", s)          # opt-out
        self.assertIn('[$net getSigType] ne "SIGNAL"', s)  # never clock / power nets

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
    def test_tcl_balanced(self):
        r = subprocess.run(["tclsh"], input="set f [open %s]; set s [read $f]; puts [info complete $s]" % TCL,
                           capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "1", r.stderr)


if __name__ == "__main__":
    unittest.main()
