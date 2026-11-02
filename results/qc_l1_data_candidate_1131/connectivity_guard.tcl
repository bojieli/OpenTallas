# Whole existing ITerm/BTerm incidence and net-class identity: no timing queries.
proc incidence {b} {
 set d {}
 foreach i [$b getInsts] {
  foreach t [$i getITerms] {
   set n [$t getNet];set v {UNCONNECTED};if {$n ne "NULL"} {set v [list [$n getName] [$n getSigType] [$n isSpecial]]}
   lappend v [$t isSpecial]
   dict set d [list IT [$i getName] [[$t getMTerm] getName]] $v
  }
 }
 foreach t [$b getBTerms] {
  set n [$t getNet];set v {UNCONNECTED};if {$n ne "NULL"} {set v [list [$n getName] [$n getSigType] [$n isSpecial]]}
  dict set d [list BT [$t getName]] $v
 }
 return $d
}
proc net_ids {b} {set d {};foreach n [$b getNets] {dict set d [$n getName] [list [$n getSigType] [$n isSpecial]]};return $d}
proc require_same_dict {expected actual msg} {
 require [expr {[lsort [dict keys $expected]] eq [lsort [dict keys $actual]]}] "$msg keys"
 dict for {k v} $expected {require [expr {$v eq [dict get $actual $k]}] "$msg $k"}
}
set incidence_before [incidence $b]
set nets_before [net_ids $b]
