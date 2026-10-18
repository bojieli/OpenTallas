# ELEM-GAPS/HBMN1 r2 (10-18) PRE_GLOBAL_PLACE, before io_flop_at_pins: the ring pin-word copy flops
# g_cp[b].u_p0 (cw_i[b] W face -> pin0_q[b] N face) and g_cp[b].u_p1 (ccw_i[b] E face -> pin1_q[b] N face) are fixed
# FIRM at the midpoint of their two pins (row / site snapped), so the input wire and the output wire share the
# distance (n1: copies at the input face, launch 286 ps; worst pair ~130 um Manhattan -> <= ~65 um per side).
# io_flop_at_pins keeps fixed flops where they are; cp_mid_release.tcl (PRE_DETAIL_PLACE) returns them to PLACED for DPL.
# Placement only, 0 cycles.
set cm_blk [ord::get_db_block]
set cm_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cm_rows {}
foreach row [$cm_blk getRows] {
  set box [$row getBBox]
  lappend cm_rows [list [$box yMin] [$box xMin] [$box xMax] [$row getSpacing] [$row getOrient]]
}
proc cm_center {bt} {
  set bb [$bt getBBox]
  return [list [expr {([$bb xMin] + [$bb xMax]) / 2.0}] [expr {([$bb yMin] + [$bb yMax]) / 2.0}]]
}
set cm_n 0
set cm_fh [open $::env(RESULTS_DIR)/ot_cp_mid.txt w]
foreach inst [$cm_blk getInsts] {
  set nm [$inst getName]
  if {![regexp {g_cp\\?\[([0-9]+)\\?\][./]u_p([01])[./]} $nm -> b side]} continue
  if {![string match *DFF* [[$inst getMaster] getName]]} continue
  if {$side eq "0"} { set ip "cw_i\[$b\]"; set op "pin0_q\[$b\]" } else { set ip "ccw_i\[$b\]"; set op "pin1_q\[$b\]" }
  set bi [$cm_blk findBTerm $ip]; set bo [$cm_blk findBTerm $op]
  if {$bi eq "NULL" || $bo eq "NULL"} { error "CP_MID: missing port $ip / $op for $nm" }
  lassign [cm_center $bi] x0 y0; lassign [cm_center $bo] x1 y1
  set mx [expr {($x0 + $x1) / 2.0}]; set my [expr {($y0 + $y1) / 2.0}]
  set h [[$inst getMaster] getHeight]; set w [[$inst getMaster] getWidth]
  set best {}; set bd Inf
  foreach r $cm_rows {
    lassign $r ry rx ex pitch orient
    set d [expr {abs($ry + $h / 2.0 - $my)}]
    if {$d < $bd} { set bd $d; set best $r }
  }
  lassign $best ry rx ex pitch orient
  set x [expr {$rx + round(($mx - $w / 2.0 - $rx) / $pitch) * $pitch}]
  set x [expr {max($rx, min($ex - $w, $x))}]
  $inst setOrient $orient
  $inst setLocation [expr {int($x)}] [expr {int($ry)}]
  $inst setPlacementStatus FIRM
  puts $cm_fh $nm
  incr cm_n
}
close $cm_fh
puts "CP_MID fixed $cm_n ring copy flops at their pin midpoints"
if {$cm_n != 560} { error "CP_MID: expected 560 ring copy flops (280 per direction), found $cm_n (netlist renamed / merged?)" }
