read_db /odb/3_place.odb
set rsp_blk [ord::get_db_block]
set rsp_db [ord::get_db]
set rsp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rsp_sw 0.054; set rsp_sh 0.27; set rsp_ox 4.32; set rsp_oy 4.32; set rsp_status FIRM
proc rsp_inst {name master x y} {
  global rsp_blk rsp_db rsp_dbu rsp_sw rsp_sh rsp_ox rsp_oy rsp_status
  set m [$rsp_db findMaster $master]
  if {$m eq "NULL"} { error "REG_SPINE: no master $master" }
  set i [odb::dbInst_create $rsp_blk $m $name]
  set sx [expr {$rsp_ox + round(($x - $rsp_ox) / $rsp_sw) * $rsp_sw}]
  set sy [expr {$rsp_oy + round(($y - $rsp_oy) / $rsp_sh) * $rsp_sh}]
  # setOrient transforms the existing origin/bbox. Set the orientation FIRST,
  # then ask OpenDB for the planned lower-left location; reversing these calls
  # shifts every MX body down one row and overlaps adjacent folded pad rows.
  if {(round(($sy - $rsp_oy) / $rsp_sh) % 2) == 1} { $i setOrient MX } else { $i setOrient R0 }
  $i setLocation [expr {round($sx * $rsp_dbu)}] [expr {round($sy * $rsp_dbu)}]
  $i setPlacementStatus $rsp_status
  return $i
}
foreach y {100.44 100.71} orient {R0 MX} {
 set i [rsp_inst probe_actual_$orient BUFx4_ASAP7_75t_R 50 $y]
 set r [$i getBBox]
 set x [expr {round((4.32+round((50-4.32)/0.054)*0.054)*$rsp_dbu)}]
 set yy [expr {round($y*$rsp_dbu)}]
 if {[$i getOrient] ne $orient || [$r xMin]!=$x || [$r yMin]!=$yy || [$r yMax]!=$yy+270} {error "ORIENT_BODY_FAIL $orient bbox=[$r xMin],[$r yMin],[$r xMax],[$r yMax]"}
 puts "RSP_ORIENT_BODY_PASS orient=$orient row_y=$y bbox=[$r xMin],[$r yMin],[$r xMax],[$r yMax] status=[$i getPlacementStatus]"
}
exit
