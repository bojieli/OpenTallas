read_db /work/input.odb
proc source_state {} {
 set out {}
 foreach i [[ord::get_db_block] getInsts] {
  set pins {}
  foreach t [$i getITerms] {if {[[$t getMTerm] getSigType] in {POWER GROUND}} continue;set n [$t getNet];lappend pins [list [[$t getMTerm] getName] [expr {$n eq "NULL" ? "" : [$n getName]}]]}
  lappend out [list [$i getName] [[$i getMaster] getName] [$i getOrigin] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [lsort $pins]]
 }
 foreach n [[ord::get_db_block] getNets] {lappend out [list NET [$n getName] [$n getSigType] [$n isDoNotTouch] [$n isSpecial]]}
 foreach t [[ord::get_db_block] getBTerms] {set n [$t getNet];lappend out [list PORT [$t getName] [expr {$n eq "NULL" ? "" : [$n getName]}]]}
 return [lsort $out]
}
set before [source_state]
set f [open /work/open_pg.tsv w];puts $f "instance\tmaster\tpin\trole\tdont_touch";set count 0;array set masters {}
foreach i [[ord::get_db_block] getInsts] {foreach t [$i getITerms] {set mt [$t getMTerm];set role [$mt getSigType];if {$role ni {POWER GROUND}} continue;if {[$t getNet] ne "NULL"} continue;incr count;incr masters([[$i getMaster] getName]);puts $f "[$i getName]\t[[$i getMaster] getName]\t[$mt getName]\t$role\t[$i isDoNotTouch]"}};close $f
puts "RED_OPEN_PG_BEFORE $count"
foreach m [lsort [array names masters]] {puts "RED_OPEN_PG_MASTER $m $masters($m)"}
source /work/pg_connect.tcl
ot_pg_connect_all red_actual_cts_pg
ot_pg_require_bound red_actual_cts_pg
if {$before ne [source_state]} {error "RED_PG_SOURCE_GUARD_CHANGED"}
puts "RED_PG_SOURCE_GUARD_PASS all masters poses statuses DATA CLOCK BTerms netflags"
write_db /work/red_cts_pg_bound.odb
