# Generated from actual slw_fe_v1 control FFs; no guessed sites.
set fup_blk [ord::get_db_block]
set fup_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fup_rows {
 {{^u_bound\.u_core\.g_local_reset\.u_agu\.rs1\$_DFF} 79.528500 259.015000}
 {{^u_bound\.u_core\.g_local_reset\.u_agu\.(?:rs2|rst)\$_DFF} 5.697000 15.290000}
 {{^u_bound\.u_core\.g_local_reset\.u_chu\.rs1\$_DFF} 80.284500 374.507500}
 {{^u_bound\.u_core\.g_local_reset\.u_chu\.(?:rs2|rst)\$_DFF} 7.209000 246.275000}
 {{^u_bound\.u_core\.g_local_reset\.u_cmd\.rs1\$_DFF} 377.699000 563.895000}
 {{^u_bound\.u_core\.g_local_reset\.u_cmd\.(?:rs2|rst)\$_DFF} 602.038000 625.050000}
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
