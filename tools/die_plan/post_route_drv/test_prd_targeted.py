import pathlib
import subprocess
import tempfile
import unittest

class Targeted(unittest.TestCase):
 def test_guards_restore_on_success_and_failure(self):
  helper=pathlib.Path(__file__).with_name('prd_targeted.tcl')
  with tempfile.TemporaryDirectory() as d:
   script=r'''
set ::env(REPORTS_DIR) [lindex $argv 0]
source [lindex $argv 1]
set dt(keep) 0; set dt(other) 0; set dt(frozen) 1
foreach n {keep other frozen} {
 proc $n {method args} [string map [list @N@ $n] {
  switch $method {
   getSigType {return SIGNAL}
   isDoNotTouch {return $::dt(@N@)}
   getName {return @N@}
   setDoNotTouch {set ::dt(@N@) [lindex $args 0]}
  }
 }]
}
namespace eval ord {proc get_db_block {} {return block}}
proc block {method} {return {keep other frozen}}
proc get_pins {args} {return [lindex $args end]}
proc get_ports {args} {return {}}
proc get_nets {args} {return keep}
proc get_full_name {arg} {return $arg}
proc report_check_types {args} {
 set f [open [lindex $args end] w]
 puts $f {U/D 10.0 12.0 -2.0 (VIOLATED)}; close $f
}
proc repair_design {args} {
 if {$args ne {-slew_margin 20}} {error "wrong repair args: $args"}
 if {$::dt(keep) || !$::dt(other) || !$::dt(frozen)} {error "wrong guard state"}
 if {$::fail} {error "native repair failure"}
}
set fail 0
ottarget_placeholder
if {$dt(other) || !$dt(frozen)} {error "guard leaked on success"}
set fail 1
if {![catch {ottarget_placeholder} msg] || $msg ne {native repair failure}} {error "native error lost: $msg"}
if {$dt(other) || !$dt(frozen)} {error "guard leaked on failure"}
puts PASS
'''.replace('ottarget_placeholder','ot_prd_repair_targeted {-slew_margin 20}')
   p=pathlib.Path(d)/'test.tcl';p.write_text(script)
   run=subprocess.run(['tclsh',str(p),d,str(helper)],capture_output=True,text=True)
   self.assertEqual(run.returncode,0,run.stderr)
   self.assertIn('PASS',run.stdout)
if __name__=='__main__':unittest.main()
