# Source-owned L2 strip floorplan: leave FIRM face banks in place; cluster the
# remaining control/datapath logic in the clear central area. No netlist edits.
uplevel #0 {
set l2_b [ord::get_db_block]
set l2_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set l2_name l2_movable_logic
if {[$l2_b findRegion $l2_name] ne "NULL"} { error "L2_LOGIC_REGION duplicate region" }
set l2_r [odb::dbRegion_create $l2_b $l2_name]
$l2_r setRegionType EXCLUSIVE
odb::dbBox_create $l2_r [expr {round(86.4*$l2_dbu)}] [expr {round(12.96*$l2_dbu)}] [expr {round(172.8*$l2_dbu)}] [expr {round(30.24*$l2_dbu)}]
set l2_g [odb::dbGroup_create $l2_r $l2_name]
set l2_n 0
set l2_area 0.0
foreach l2_i [$l2_b getInsts] {
  set l2_m [$l2_i getMaster]
  if {[$l2_m isBlock]} { continue }
  if {[$l2_i getPlacementStatus] ni {PLACED NONE UNPLACED SUGGESTED}} { continue }
  $l2_g addInst $l2_i
  incr l2_n
  set l2_area [expr {$l2_area+double([$l2_m getWidth])*[$l2_m getHeight]/$l2_dbu/$l2_dbu}]
}
if {$l2_n == 0 || $l2_area > 0.6*86.4*17.28} { error "L2_LOGIC_REGION no logic or planned area exceeds60percent: $l2_n $l2_area" }
puts "L2_LOGIC_REGION movable=$l2_n area_um2=$l2_area rect=86.4,12.96,172.8,30.24 fixed_face_banks_preserved=1"
}
