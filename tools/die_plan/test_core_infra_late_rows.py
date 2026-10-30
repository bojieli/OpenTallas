"""Pure Tcl row-selection controls; no OpenROAD or placement run required."""
import pathlib
import shutil
import subprocess
import unittest

SOURCE = pathlib.Path(__file__).with_name("core_infra_late.tcl")

HARNESS = r'''
proc clock_tree_synthesis {args} {}
source SOURCE
set ::ot_ci_u 1000
set ::calls [dict create]
proc hit {key} {dict incr ::calls $key}
proc row {name method args} {
  set r [dict get $::rows $name]
  switch $method {
    getOrigin {hit origin; return [lrange $r 0 1]}
    getSite {return site_$name}
    getOrient {return [lindex $r 3]}
  }
  error "unexpected row method $method"
}
proc site {name method} {return [lindex [dict get $::rows $name] 2]}
proc block {name method args} {
  switch $method {
    getRows {hit $name; return [dict get $::blocks $name]}
    findInst {return inst}
  }
  error "unexpected block method $method"
}
proc install_rows {name records} {
  set names {}; set n 0
  foreach r $records {
    set rn ${name}_r[incr n]; dict set ::rows $rn $r; lappend names $rn
    interp alias {} $rn {} row $rn
    interp alias {} site_$rn {} site $rn
  }
  dict set ::blocks $name $names
  interp alias {} $name {} block $name
}
proc old_row {h y} {
  set best 1e99; set chosen {}; set ordinal 0
  foreach r [$::ot_ci_b getRows] {
    lassign [$r getOrigin] rx ry
    set d [expr {abs($ry + $h / 2.0 - $y * $::ot_ci_u)}]
    if {$d < $best} {set best $d; set chosen [list $ordinal $r $rx $ry]}
    incr ordinal
  }
  return $chosen
}
proc check {condition message} {if {![uplevel 1 [list expr $condition]]} {error $message}}
proc master {method} {
  switch $method {getWidth {return 53} getHeight {return $::height}}
}
proc inst {method args} {
  switch $method {
    getMaster {return master}
    findITerm {return term}
    setOrient - setLocation - setPlacementStatus {dict set ::placed $method $args; return}
  }
  error "unexpected instance method $method"
}
namespace eval ord {proc get_db {} {return db}}
proc db {method name} {return master}
set ::rows {}; set ::blocks {}; set ::ot_ci_cells {}
'''


@unittest.skipUnless(shutil.which("tclsh"), "tclsh required")
class LateRowsTest(unittest.TestCase):
    def run_tcl(self, body):
        script = HARNESS.replace("SOURCE", "{" + str(SOURCE) + "}") + body
        # tclsh stdin otherwise exits zero on Tcl errors: explicit catch controls rc.
        result = subprocess.run(["tclsh"], input="if {[catch {\n" + script + "\n} msg opts]} {puts stderr $msg; exit 1}\n", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_old_selection_cell_coordinates_and_cache(self):
        self.run_tcl(r'''
install_rows A {{103 300 54 MX} {-91 -240 108 R0} {900 300 27 R180} {12 30 54 R0} {7 -510 27 MX}}
install_rows B {{-3 400 108 R180} {8 -400 54 R0}}
foreach b {A B A} {
  set ::ot_ci_b $b
  foreach h {269 270 271 541} {
    set ::height $h
    foreach y {-2 -0.3755 -0.375 -0.105 0 0.1645 0.3 0.435 0.565 2} {
      set expected [old_row $h $y]
      set actual [ot_ci_late_row test $h $y]
      check {$actual eq $expected} "row mismatch $b $h $y: $actual != $expected"
      lassign $expected ordinal r rx ry
      foreach x {-2.3 -0.027 0 1.234} {
        set ::placed {}; ot_ci_late_cell foo BUF $x $y {}
        set sw [[$r getSite] getWidth]
        set xx [expr {$rx + int(round(($x * $::ot_ci_u - 53 / 2.0 - $rx) / $sw)) * $sw}]
        check {[dict get $::placed setLocation] eq [list $xx $ry]} "location changed"
        check {[dict get $::placed setOrient] eq [list [$r getOrient]]} "orientation changed"
      }
    }
  }
}
# Explicit opposite-Y tie: row 0 wins despite sorting Y ascending.
set ::ot_ci_b A
check {[lindex [ot_ci_late_row test 270 0.3] 0] == 0} "first ordinal tie changed"
set before $::calls
for {set i 0} {$i < 1000} {incr i} {ot_ci_late_row repeat 270 0.5}
check {$before eq $::calls} "cache repeated getRows/getOrigin"
check {[dict size $::ot_ci_late_row_cache] == 2} "blocks not separately cached"
''')

    def test_empty_block_cached_and_failure_unchanged(self):
        self.run_tcl(r'''
install_rows E {}; set ::ot_ci_b E
foreach name {first second} {
  check {[catch {ot_ci_late_row $name 270 0} msg]} "empty rows accepted"
  check {$msg eq "OT_CORE_INFRA_NO_ROWS $name"} "failure changed: $msg"
}
check {[dict get $::calls E] == 1} "empty inventory not cached"
''')


if __name__ == "__main__":
    unittest.main()
