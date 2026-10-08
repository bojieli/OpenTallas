"""Exercise the actual Tcl checker with classified OpenDB-shaped objects."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
CHECK=ROOT/'physical/ha2_truecredit_20261007/check_signal_identity.tcl'
FIXTURE=r'''
set case [lindex $argv 0]
set objects [dict create]
proc object {name fields} {
 global objects
 dict set objects $name $fields
 interp alias {} $name {} get_object $name
}
proc get_object {name method args} {
 global objects
 return [dict get $objects $name $method]
}
object blk [dict create getBTerms {a b clk vdd vss} getDieArea die]
object die [dict create xMin 0 yMin 0 xMax 100 yMax 100]
foreach term {a b clk vdd vss unexpected} {
 set type SIGNAL
 if {$term eq "clk"} {set type CLOCK}
 if {$term eq "vdd"} {set type POWER}
 if {$term eq "vss"} {set type GROUND}
 object $term [dict create getName $term getSigType $type getBPins ${term}_pin]
 set boxes {}
 set count [expr {$type eq "POWER" || $type eq "GROUND" ? 7 : 1}]
 for {set i 0} {$i<$count} {incr i} {
  set box ${term}_box$i
  object $box [dict create xMin 1 yMin 1 xMax 2 yMax 2]
  lappend boxes $box
 }
 object ${term}_pin [dict create getBoxes $boxes]
}
switch $case {
 pass {}
 unexpected {dict set objects blk getBTerms {a b clk vdd vss unexpected}}
 missing {dict set objects blk getBTerms {a clk vdd vss}}
 wrong_pg {dict set objects b getSigType POWER}
 duplicate_box {dict set objects a_pin getBoxes {a_box0 a_box0}}
 outside {dict set objects a_box0 xMax 101}
}
namespace eval ord {proc get_db_block {} {return blk}}
if {[catch {ot_ha2_check_signal_identity {a b clk}} result]} {
 puts stderr $result
 exit 1
}
puts "RESULT $result"
'''


class SignalPinChecker(unittest.TestCase):
    def run_case(self,case):
        # Tcl stdin execution does not propagate errors reliably: execute a
        # sourced temporary script and let the fixture explicitly exit on fail.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.tcl'
            path.write_text('source {'+str(CHECK)+'}\n'+FIXTURE)
            return subprocess.run(['tclsh',str(path),case],capture_output=True,text=True)

    def test_classified_power_ground_boxes_excluded(self):
        r=self.run_case('pass')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('signals=3 pg_terms=2 pg_boxes=14',r.stdout)

    def test_signal_identity_count_and_box_failures_reject(self):
        for case,marker in [('unexpected','unexpected truecredit signal'),
                            ('missing','missing truecredit signal'),
                            ('wrong_pg','expected truecredit signal classified POWER'),
                            ('duplicate_box','expected1 box got2'),
                            ('outside','signal box outside die')]:
            with self.subTest(case=case):
                r=self.run_case(case)
                self.assertNotEqual(r.returncode,0)
                self.assertIn(marker,r.stderr)


if __name__=='__main__':
    unittest.main()
