"""Exact fixed-body lookup agrees with the original full checkpoint census."""
from pathlib import Path
import subprocess
import unittest

class OccupancyTest(unittest.TestCase):
    def test_live_bodies_and_order(self):
        source=Path(__file__).resolve().parents[1]/'tools/die_plan/core_infra.tcl'
        script=r'''
source SOURCE
namespace eval ord {proc get_db_block {} {return block}; proc get_db_tech {} {return tech}}
proc tech {method args} {return 1000}
proc block {method args} {return $::insts}
proc master {method args} {return 0}
proc blockmaster {method args} {return 1}
proc object {name method args} {
 switch $method {
 getMaster {return [expr {[dict get $::objects $name block] ? "blockmaster" : "master"}]}
 getPlacementStatus {return [dict get $::objects $name status]}
 getBBox {return ${name}_box}
 getName {return $name}
 }
}
proc bbox {name method args} {
 set axis [dict create xMin 0 yMin 1 xMax 2 yMax 3]
 return [lindex [dict get $::objects $name rect] [dict get $axis $method]]
}
proc add {name rect status isblock} {
 dict set ::objects $name [dict create rect $rect status $status block $isblock]
 interp alias {} $name {} object $name
 interp alias {} ${name}_box {} bbox $name
 lappend ::insts $name
}
set ::objects {};set ::insts {}
expr {srand(1029)}
for {set i 0} {$i<300} {incr i} {
 set x [expr {int(rand()*100000)-20000}];set y [expr {int(rand()*100000)-20000}]
 add i$i [list $x $y [expr {$x+int(rand()*15000)}] [expr {$y+int(rand()*15000)}]] [lindex {FIRM LOCKED COVER PLACED NONE} [expr {$i%5}]] [expr {$i%17==0}]
}
ot_ci_begin
proc overlaps {items x0 y0 x1 y1} {
 set result {}
 foreach i $items {
 if {![[$i getMaster] isBlock] && [$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
 set r [$i getBBox]
 if {$x0<[$r xMax] && $x1>[$r xMin] && $y0<[$r yMax] && $y1>[$r yMin]} {lappend result $i}
 }
 return $result
}
proc check {} {
 for {set k 0} {$k<400} {incr k} {
 set x [expr {int(rand()*120000)-30000}];set y [expr {int(rand()*120000)-30000}]
 set xx [expr {$x+int(rand()*15000)}];set yy [expr {$y+int(rand()*15000)}]
 set expected [overlaps $::insts $x $y $xx $yy]
 set actual [overlaps [ot_ci_occ_candidates $x $y $xx $yy] $x $y $xx $yy]
 if {$expected ne $actual} {error "census mismatch: $expected != $actual"}
 }
}
check
# Existing body moves across buckets; new clock cell becomes fixed after creation.
dict set ::objects i0 rect {-50000 -50000 -40000 -40000};ot_ci_occ_add i0
add newclock {60000 60000 71000 71000} FIRM 0;ot_ci_occ_add newclock
# Repeated insertion must not duplicate a diagnostic candidate.
ot_ci_occ_add newclock
check
puts PASS
'''.replace('SOURCE','{'+str(source)+'}')
        result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
        self.assertEqual(result.stderr,'')
        self.assertEqual(result.stdout.strip(),'PASS')
if __name__=='__main__':unittest.main()
