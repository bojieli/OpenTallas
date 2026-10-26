# Generated from actual sle_fe_v1 control FFs; no guessed sites.
set fup_blk [ord::get_db_block]
set fup_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fup_rows {
 {{^u_bound\.u_core\.g_local_reset\.u_agu\.rs1\$_DFF} 215.368250 450.164250}
 {{^u_bound\.u_core\.g_local_reset\.u_agu\.(?:rs2|rst)\$_DFF} 276.134500 398.668500}
 {{^u_bound\.u_core\.g_local_reset\.u_chu\.rs1\$_DFF} 215.712500 525.960000}
 {{^u_bound\.u_core\.g_local_reset\.u_chu\.(?:rs2|rst)\$_DFF} 276.823000 550.260000}
 {{^u_bound\.u_core\.g_local_reset\.u_cmd\.rs1\$_DFF} 215.780000 533.655000}
 {{^u_bound\.u_core\.g_local_reset\.u_cmd\.(?:rs2|rst)\$_DFF} 276.958000 565.650000}
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
