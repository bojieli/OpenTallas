"""Physical keepouts must never erase signal-bearing cells."""
import pathlib
import subprocess
import unittest

HELPER = pathlib.Path(__file__).with_name("keepout_phys.tcl")
FIXTURE = r'''
set deleted 0
proc b {op} {return {i}}
proc i {op} {switch $op {getMaster {return m} getName {return TAP_fixture} getBBox {return box} getITerms {return {it}}}}
proc m {op} {return CORE_WELLTAP}
proc box {op} {switch $op {xMin - yMin {return 1} xMax - yMax {return 2}}}
proc it {op} {global signal; return $signal}
namespace eval odb {proc dbInst_destroy {i} {global deleted; incr deleted}}
'''

class KeepoutPhysicalTest(unittest.TestCase):
    def run_tcl(self, signal, rectangle):
        text = f"source {{{HELPER}}}\n" + FIXTURE + f"\nset signal {signal}\n"
        text += f"set rc [catch {{ot_clear_keepout_physical b {{{rectangle}}} fixture}} msg]\n"
        text += 'puts "RESULT $rc $deleted $msg"\n'
        return subprocess.run(["tclsh"], input=text, text=True, capture_output=True, check=True).stdout

    def test_only_overlapping_physical_removed(self):
        self.assertIn("RESULT 0 1 1", self.run_tcl(0, "{0 0 3 3}"))

    def test_outside_reservation_preserved(self):
        self.assertIn("RESULT 0 0 0", self.run_tcl(0, "{3 3 4 4}"))

    def test_signal_bearing_name_match_fails_closed(self):
        self.assertIn("RESULT 1 0 keepout physical cell has signal pins", self.run_tcl(1, "{0 0 3 3}"))

if __name__ == "__main__":
    unittest.main()
