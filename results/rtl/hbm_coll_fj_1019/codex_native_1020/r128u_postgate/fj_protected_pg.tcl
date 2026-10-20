read_db $::env(AUDIT_ODB)
set b [ord::get_db_block];set c {};set names {};set n 0
foreach i [$b getInsts] {
 if {![$i isDoNotTouch]} continue
 set bad 0
 foreach t [$i getITerms] {if {[$t getSigType] ni {POWER GROUND}} continue;set net [$t getNet];if {$net eq "NULL" || $net eq ""} {set bad 1}}
 if {$bad} {dict incr c [list [[$i getMaster] getName] [$i getPlacementStatus]];incr n;if {[llength $names]<20} {lappend names [$i getName]}}
}
puts "FJ_PROTECTED_PG_MISSING n=$n groups=$c examples=$names"
