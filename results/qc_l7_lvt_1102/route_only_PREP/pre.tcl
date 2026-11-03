source /work/pg_connect.tcl
ot_pg_require_bound l7_native_drt_pre
set ::l7_original {};set ::l7_nets {}
set b [ord::get_db_block]
foreach i [$b getInsts] {
 set ports {};foreach t [$i getITerms] {set n [$t getNet];dict set ports [[$t getMTerm] getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]}
 dict set ::l7_original [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] $ports]
}
foreach n [$b getNets] {lappend ::l7_nets [$n getName]}
if {[llength [$b getInsts]] != 272550 || [llength [$b getNets]] != 279951} {error "L7 actual guarded candidate inventory differs"}
puts L7_DRT_PRE_SOURCE_PG_GUARD_READY
