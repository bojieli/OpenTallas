read_db $::env(AUDIT_ODB)
foreach net {VDD VSS} {
 set rc [catch {check_power_grid -net $net -floorplanning} why]
 puts "FJ_PG_CONTINUITY net=$net rc=$rc message=$why"
}
set b [ord::get_db_block]
set f [open $::env(AUDIT_PIN_REPORT) w]
puts $f "instance\tmaster\tstatus\tdont_touch\tVDD\tVSS"
foreach i [$b getInsts] {
 set bad 0;set nets {}
 foreach n {VDD VSS} {set t [$i findITerm $n];set v "";if {$t ne "NULL" && $t ne ""} {set x [$t getNet];if {$x ne "NULL" && $x ne ""} {set v [$x getName]}};lappend nets $v;if {$v eq ""} {set bad 1}}
 if {$bad || [[$i getMaster] isBlock]} {puts $f "[$i getName]\t[[$i getMaster] getName]\t[$i getPlacementStatus]\t[$i isDoNotTouch]\t[join $nets \t]"}
}
close $f
