# Release only the four owned peripheral exclusions for clock-tree buffers.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set keys {}
foreach rect {{4.32 4.32 125.28 145.68} {174.96 4.32 295.68 145.68} {125.28 4.32 174.96 48.60} {125.28 89.64 174.96 145.68}} {
 set key {}
 foreach v $rect {lappend key [expr {round($v*$dbu)}]}
 lappend keys $key
}
set removed 0
foreach b [$block getBlockages] {
 set bb [$b getBBox]
 set key [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
 if {[lsearch -exact $keys $key] >= 0} {odb::dbBlockage_destroy $b; incr removed}
}
if {$removed != 4} {error "expected four owned periphery blockages, removed $removed"}
set nmacro 0
foreach b [$block getBlockages] {if {[$b getInstance] != "NULL"} {incr nmacro}}
if {$nmacro <56} {error "missing explicit macro CTS obstructions: $nmacro"}
puts "OT_HEAD_NATIVE_CTS_PERIPHERY_RELEASED $removed macro_obstructions=$nmacro"
source /src/physical/s81_die_views/hbglue/parent_diamond.tcl
