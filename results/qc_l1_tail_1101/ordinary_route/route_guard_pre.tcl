proc l1_route_need {ok msg} {if {!$ok} {error $msg}}
set ::l1_route_original {};set ::l1_route_clock {}
foreach i [[ord::get_db_block] getInsts] {
 set ports {};foreach t [$i getITerms] {set n [$t getNet];dict set ports [[$t getMTerm] getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]}
 dict set ::l1_route_original [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] $ports]
}
foreach n [[ord::get_db_block] getNets] {if {[$n getSigType] ne "CLOCK"} continue;foreach t [$n getITerms] {lappend ::l1_route_clock [list [$n getName] [[$t getInst] getName] [[$t getMTerm] getName]]}}
source /work/pg_connect.tcl
ot_pg_require_bound l1_route_pre
puts L1_NATIVE_DRT_PRE_SOURCE_GUARD_READY
