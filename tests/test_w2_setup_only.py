import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class SetupOnlyTest(unittest.TestCase):
    def test_dispatch_and_no_constraint_changes(self):
        hook = ROOT/'physical/hbm_w2_rb_station_20261006/setup_only.tcl'
        script = '''
proc repair_timing {args} {return $args}
source {%s}
source {%s}
set got [repair_timing -hold_margin 35 -setup_margin 0 -verbose]
if {$got ne {-setup -hold_margin 35 -setup_margin 0 -verbose}} {error $got}
if {[repair_timing -setup -verbose] ne {-setup -verbose}} {error duplicate}
if {![catch {repair_timing -hold} msg]} {error "hold dispatched"}
puts PASS
''' % (hook, hook)
        p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, '')
        self.assertIn('PASS', p.stdout)
        # No STA constraint-changing command is stubbed: Tcl would reject one.

if __name__ == '__main__':
    unittest.main()
