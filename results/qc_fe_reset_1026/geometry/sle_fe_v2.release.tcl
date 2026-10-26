# Generated from actual sle_fe_v2 control FFs; no guessed sites.
set fup_blk [ord::get_db_block]
set fup_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fup_rows {
 {{^u_bound\.u_core\.g_local_reset\.u_agu\.rs1\$_DFF} 216.920750 454.065750}
 {{^u_bound\.u_core\.g_local_reset\.u_agu\.(?:rs2|rst)\$_DFF} 279.725500 406.201500}
 {{^u_bound\.u_core\.g_local_reset\.u_chu\.rs1\$_DFF} 216.887000 514.755000}
 {{^u_bound\.u_core\.g_local_reset\.u_chu\.(?:rs2|rst)\$_DFF} 279.658000 527.580000}
 {{^u_bound\.u_core\.g_local_reset\.u_cmd\.rs1\$_DFF} 217.022000 540.270000}
 {{^u_bound\.u_core\.g_local_reset\.u_cmd\.(?:rs2|rst)\$_DFF} 279.928000 578.610000}
}
foreach row $fup_rows {
 lassign $row pat x y
 set matches {}
 foreach i [$fup_blk getInsts] {
  set m [$i getMaster]
  if {![string match *DFF* [$m getName]]} continue
  set name [string map {\\ {} / .} [$i getName]]
  if {[regexp $pat $name]} {lappend matches $i}
 }
 if {[llength $matches] != 1} {error "FUP reset anchor $pat found [llength $matches] FFs"}
 set i [lindex $matches 0]
 $i setPlacementStatus PLACED
}
