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
set ::env(OT_PRD_TIE_SPLIT) 0
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
 def test_explicit_allowlist_rejects_report_expansion(self):
  helper=pathlib.Path(__file__).with_name('prd_targeted.tcl')
  original=helper.read_text()
  with tempfile.TemporaryDirectory() as d:
   script=r'''
set ::env(REPORTS_DIR) [lindex $argv 0]
source [lindex $argv 1]
set ::ot_prd_local_targets [dict create keep 1]
set dt(keep) 0;set dt(other) 0;set dt(frozen) 1
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
proc get_pins {args} {return other/D}
proc get_ports {args} {return {}}
proc get_nets {args} {return other}
proc get_full_name {arg} {return $arg}
proc report_check_types {args} {
 set f [open [lindex $args end] w]
 puts $f {other/D 10.0 12.0 -2.0 (VIOLATED)};close $f
}
proc repair_design {args} {
 if {$::dt(keep) || !$::dt(other) || !$::dt(frozen)} {error ALLOWLIST_ESCAPED}
}
ot_prd_repair_targeted {-slew_margin 20}
if {$dt(other) || !$dt(frozen)} {error GUARD_LEAK}
puts PASS
'''
   p=pathlib.Path(d)/'test.tcl';p.write_text(script)
   result=subprocess.run(['tclsh',str(p),d,str(helper)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertIn('PASS',result.stdout)
   mutant=pathlib.Path(d)/'mutant.tcl'
   mutant.write_text(original.replace('if {[info exists ::ot_prd_local_targets]} { set keep $::ot_prd_local_targets }',''))
   result=subprocess.run(['tclsh',str(p),d,str(mutant)],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0)
   self.assertIn('ALLOWLIST_ESCAPED',result.stderr)
 def test_bracketed_violator_is_not_guarded(self):
  helper=pathlib.Path(__file__).with_name('prd_targeted.tcl')
  with tempfile.TemporaryDirectory() as d:
   script=r"""
set ::env(REPORTS_DIR) [lindex $argv 0]
set ::env(OT_PRD_TIE_SPLIT) 0
set ::env(OT_PRD_TARGET_SLEW_PS) 288
source [lindex $argv 1]
set dt(k) 0; set dt(o) 0
proc k {method args} {switch $method {getSigType {return SIGNAL} isDoNotTouch {return $::dt(k)} getName {return {u.a\[1\]}} setDoNotTouch {set ::dt(k) [lindex $args 0]}}}
proc o {method args} {switch $method {getSigType {return SIGNAL} isDoNotTouch {return $::dt(o)} getName {return other} setDoNotTouch {set ::dt(o) [lindex $args 0]}}}
namespace eval ord {proc get_db_block {} {return block}}
proc block {method} {return {k o}}
proc current_design {} {return top}
set lim {}
proc set_max_transition {v args} {lappend ::lim $v}
proc get_pins {args} {return [lindex $args end]}
proc get_ports {args} {return {}}
proc get_nets {args} {return {u.a[1]}}
proc get_full_name {arg} {return $arg}
proc report_check_types {args} {
 if {$::lim ne {288}} {error "selection limit $::lim"}
 set f [open [lindex $args end] w]; puts $f {u.d[1]/D 288.0 300.0 -12.0 (VIOLATED)}; close $f
}
proc repair_design {args} {
 if {$::lim ne {288 1e6}} {error "limit not restored before repair: $::lim"}
 if {$::dt(k) || !$::dt(o)} {error "bracketed violator guarded"}
}
ot_prd_repair_targeted {-slew_margin 20}
if {$dt(o)} {error "guard leaked"}
puts PASS
"""
   p=pathlib.Path(d)/'test.tcl';p.write_text(script)
   run=subprocess.run(['tclsh',str(p),d,str(helper)],capture_output=True,text=True)
   self.assertEqual(run.returncode,0,run.stderr)
   self.assertIn('PASS',run.stdout)

if __name__=='__main__':unittest.main()
