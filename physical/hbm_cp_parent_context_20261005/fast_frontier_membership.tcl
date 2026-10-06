# All source/repair/CTS cells retain their actual ancestry fences.
source /src/physical/hbm_cp_parent_context_20261005/cts_membership.tcl
set ot_cp_areas [dict create cp_body 0.0 cp_association 0.0]
set ot_cp_dbu [[ord::get_db_block] getDbUnitsPerMicron]
foreach ot_cp_i [[ord::get_db_block] getInsts] {
 set ot_cp_g [$ot_cp_i getGroup]
 if {$ot_cp_g eq "NULL"} {continue}
 set ot_cp_name [$ot_cp_g getName]
 if {![dict exists $ot_cp_areas $ot_cp_name]} {continue}
 set ot_cp_m [$ot_cp_i getMaster]
 set ot_cp_a [expr {double([$ot_cp_m getWidth])*[$ot_cp_m getHeight]/($ot_cp_dbu*$ot_cp_dbu)}]
 dict set ot_cp_areas $ot_cp_name [expr {[dict get $ot_cp_areas $ot_cp_name]+$ot_cp_a}]
}
foreach {ot_cp_name ot_cp_cap} {cp_body 1117.87776 cp_association 11.19744} {
 set ot_cp_actual [dict get $ot_cp_areas $ot_cp_name]
 puts "OT_FAST_FINITE_AREA region=$ot_cp_name actual=$ot_cp_actual cap=$ot_cp_cap"
 if {$ot_cp_actual>$ot_cp_cap} {error "FAST finite cell allocation exceeded $ot_cp_name $ot_cp_actual > $ot_cp_cap"}
}
