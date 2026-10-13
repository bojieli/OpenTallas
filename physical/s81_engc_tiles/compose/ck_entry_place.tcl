# dsfd_engram_c PRE_DETAIL_PLACE (el1013-s81-engram 2026-10-13): each clock entry chain sits AT its child's clock pin.
# Global placement strings a chain along the line from the clock root to the pin, so an HB4xp67 drives 100+ um of wire
# (CTS-stop run c4: RSZ-3006 on u_hdly_ck_sink c[3], 293 ps slew at the sink pin without the chain).  Here every chain
# cell is moved onto its child's ck pin; detail placement legalises them in the nearest rows, so the chain nets are a
# few um, the delay is the cells' own, and the top tree's leaf lands at the child.
source /src/physical/s81_engc_tiles/compose/ck_entry_keep.tcl
set ot_cp_b [ord::get_db_block]; set ot_cp_k 0
foreach ot_m [$ot_cp_b getInsts] {
  if {![[$ot_m getMaster] isBlock]} { continue }
  set ot_it [$ot_m findITerm ck]
  if {$ot_it eq "NULL" || $ot_it eq ""} { continue }
  set ot_bb [$ot_it getBBox]
  set ot_x [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}]; set ot_y [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]
  set ot_n [$ot_it getNet]; set ot_c 0
  while {$ot_n ne "NULL" && $ot_n ne ""} {
    set ot_d [$ot_n getFirstOutput]
    if {$ot_d eq "NULL" || $ot_d eq ""} { break }
    set ot_i [$ot_d getInst]
    if {![string match *u_hdly_ck_* [$ot_i getName]]} { break }
    $ot_i setLocation $ot_x $ot_y; $ot_i setPlacementStatus PLACED; incr ot_c; incr ot_cp_k
    set ot_n [[$ot_i findITerm A] getNet]
  }
  puts "OT_CK_ENTRY place: [$ot_m getName] ck pin ([expr {$ot_x / 1000.0}] [expr {$ot_y / 1000.0}]) chain $ot_c"
}
puts "OT_CK_ENTRY place: $ot_cp_k delay cells moved to their child's clock pin"
