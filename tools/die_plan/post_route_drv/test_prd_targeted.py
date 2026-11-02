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
namespace eval sta {proc sta_to_db_net {net} {return $net}}
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


def test_sta_bus_display_name_joins_exact_escaped_db_net(tmp_path):
 helper=pathlib.Path(__file__).with_name('prd_targeted.tcl')
 script=r'''
set ::env(REPORTS_DIR) [lindex $argv 0]
source [lindex $argv 1]
set dt(data_bus) 0;set dt(other) 0;set dt(frozen) 1;set dt(clock) 1
set repair_calls 0
foreach n {data_bus other frozen clock} {
 proc $n {method args} [string map [list @N@ $n] {
  switch $method {
   getSigType {if {"@N@" eq "clock"} {return CLOCK};return SIGNAL}
   isDoNotTouch {return $::dt(@N@)}
   getName {if {"@N@" eq "data_bus"} {return {dout\[250\]}};return @N@}
   setDoNotTouch {set ::dt(@N@) [lindex $args 0]}
  }
 }]
}
namespace eval ord {proc get_db_block {} {return block}}
namespace eval sta {proc sta_to_db_net {net} {
 if {$net ne "sta_bus"} {error "wrong STA object"}
 return [expr {$::unmapped ? "NULL" : "data_bus"}]
}}
proc block {method} {return {data_bus other frozen clock}}
proc get_pins {args} {return {}}
proc get_ports {args} {
 if {[lindex $args end] ne {dout[250]}} {error "wrong reported port"}
 return sta_port
}
proc get_nets {args} {return sta_bus}
proc get_full_name {arg} {return {dout[250]}}
proc report_check_types {args} {
 set f [open [lindex $args end] w];puts $f {dout[250] 10.0 12.0 -2.0 (VIOLATED)};close $f
}
proc repair_design {args} {
 incr ::repair_calls
 if {$::dt(data_bus) || !$::dt(other) || !$::dt(frozen) || !$::dt(clock)} {error "wrong exact target guards"}
 if {$::fail} {error "native repair failure"}
}
set unmapped 0;set fail 0
ot_prd_repair_targeted {-slew_margin 20}
if {$dt(data_bus) || $dt(other) || !$dt(frozen) || !$dt(clock)} {error "guard state not restored"}
set fail 1
if {![catch {ot_prd_repair_targeted {-slew_margin 20}} msg] || $msg ne {native repair failure}} {error "repair error lost"}
if {$dt(other) || !$dt(clock)} {error "guard leaked on native failure"}
set unmapped 1
if {![catch {ot_prd_repair_targeted {-slew_margin 20}} msg] || ![string match {*unmapped violating STA net*} $msg]} {error "unmapped net accepted"}
if {$repair_calls != 2 || $dt(other) || !$dt(clock)} {error "unmapped target mutated design"}
puts PASS
'''
 p=tmp_path/'bus.tcl';p.write_text(script)
 run=subprocess.run(['tclsh',str(p),str(tmp_path),str(helper)],capture_output=True,text=True)
 assert run.returncode==0,run.stderr
 assert 'PASS' in run.stdout
