# dsfd_engram_c PRE_GLOBAL_PLACE (el1013-s81-engram 2026-10-13, after FLOORPLAN_MARGIN of el1013-engc-compose-d21a6cf78:
# 5 child gaps < 12 um held placement rows).  The 8.64 / 10.2 um gaps between the children are aligned-pin transit seams:
# wires only, no cell belongs there.  Every child-to-child gap narrower than 12 um gets a hard placement blockage
# (physical/common_flow/macro_sliver_block.tcl), EXCEPT a 12-um pocket at a child clock pin that lies in such a gap
# (u_pb2: W-face ck pin in the pb0 | pb2 transit seam): its clock entry cells (ot_engc_ck_entry, 2-9 cells, dont_touch,
# placed at the pin by ck_entry_place.tcl) must stay at the pin.  The cluster has no other standard cell.
source /src/physical/s81_engc_tiles/compose/ck_entry_keep.tcl
set ot_sliver_um 12.0
source /src/physical/common_flow/macro_sliver_block.tcl
set ot_sb_b [ord::get_db_block]; set ot_sb_u [$ot_sb_b getDbUnitsPerMicron]; set ot_sb_h [expr {int(6.0 * $ot_sb_u)}]
set ot_sb_pins {}
foreach ot_m [$ot_sb_b getInsts] {
  if {![[$ot_m getMaster] isBlock]} { continue }
  set ot_it [$ot_m findITerm ck]
  if {$ot_it eq "NULL" || $ot_it eq ""} { continue }
  set ot_bb [$ot_it getBBox]
  lappend ot_sb_pins [list [$ot_m getName] [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}] [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]]
}
set ot_sb_k 0
foreach ot_bl [$ot_sb_b getBlockages] {
  set ot_r [$ot_bl getBBox]
  set x0 [$ot_r xMin]; set y0 [$ot_r yMin]; set x1 [$ot_r xMax]; set y1 [$ot_r yMax]
  foreach ot_p $ot_sb_pins {
    lassign $ot_p ot_nm px py
    # a pin strictly inside the gap rows (a pin on the blockage edge has its cells legalised beside it)
    if {$px <= $x0 || $px >= $x1 || $py <= $y0 || $py >= $y1} { continue }
    odb::dbBlockage_destroy $ot_bl
    if {($x1 - $x0) < ($y1 - $y0)} {
      if {$py - $ot_sb_h > $y0} { odb::dbBlockage_create $ot_sb_b $x0 $y0 $x1 [expr {$py - $ot_sb_h}] }
      if {$py + $ot_sb_h < $y1} { odb::dbBlockage_create $ot_sb_b $x0 [expr {$py + $ot_sb_h}] $x1 $y1 }
    } else {
      if {$px - $ot_sb_h > $x0} { odb::dbBlockage_create $ot_sb_b $x0 $y0 [expr {$px - $ot_sb_h}] $y1 }
      if {$px + $ot_sb_h < $x1} { odb::dbBlockage_create $ot_sb_b [expr {$px + $ot_sb_h}] $y0 $x1 $y1 }
    }
    puts "OT_ENGC_SLIVER pocket: $ot_nm ck pin ([expr {$px / double($ot_sb_u)}] [expr {$py / double($ot_sb_u)}]) keeps 12 um of rows in its seam"
    incr ot_sb_k; break
  }
}
puts "OT_ENGC_SLIVER blockages [llength [$ot_sb_b getBlockages]] ($ot_sb_k clock-pin pockets)"
