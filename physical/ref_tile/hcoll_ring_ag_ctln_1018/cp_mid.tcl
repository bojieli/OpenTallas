# ELEM-GAPS/HBMN1 r2 (10-18) PRE_GLOBAL_PLACE, before io_flop_at_pins: the ring pin-word copy flops
# g_cp[b].u_p0 (cw_i[b] W face -> pin0_q[b] N face) and g_cp[b].u_p1 (ccw_i[b] E face -> pin1_q[b] N face) are fixed
# FIRM at the midpoint of their two pins (row / site snapped), so the input wire and the output wire share the
# distance (n1: copies at the input face, launch 286 ps; worst pair ~130 um Manhattan -> <= ~65 um per side).
# io_flop_at_pins keeps fixed flops where they are; cp_mid_release.tcl (PRE_DETAIL_PLACE) returns them to PLACED for DPL.
# r3: the same midpoint for u_core.rr_d[b] (acc_rr[b] N face -> 4 mux levels -> rr_d[b] S face; r2 anchored at the
# S face as an output flop: capture 212 pins over 190) and for carry_write0/1 (cw_i/ccw_i kind bit 274 -> carry pin at
# the N corner; r2 capture cw_i[274] 228).
# r4: rr_d / carry_write sit at 0.35 of the way from the input pin (r3 probe: capture acc_rr ~200 / cw_i[274] 206 with
# 4 logic levels on the capture side, launch rr_d <= 163): the logic side gets the shorter wire.
# r5: acc_rr is pin-flopped in RTL (acc_rr_q), so u_core.rr_d is a plain S-face output flop again (no rr class); rx_slot0
# moved to the W face beside cw_i[278:273]; carry_write0/1 sit at 0.1 from cw_i/ccw_i[274] (r4 probe capture cw_i[273]
# 211: 3 compare levels + ~24 um; the flop -> carry pin wire is a pure-Q launch).
# r5b: carry_write = AND2 of flops cw_a<d> (slot & kind) and cw_b<d> (dst == qid); both at 0.1 from cw_i/ccw_i[274]
# (r5 probe: capture cw_i[273] 213 = 177 ps of logic, not wire).
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
set cm_n 0; set cm_cls [dict create cp 0 cw 0]
set cm_fh [open $::env(RESULTS_DIR)/ot_cp_mid.txt w]
foreach inst [$cm_blk getInsts] {
  set nm [$inst getName]
  if {![string match *DFF* [[$inst getMaster] getName]]} continue
  if {[regexp {g_cp\\?\[([0-9]+)\\?\][./]u_p([01])[./]} $nm -> b side]} {
    set cls cp; set wt 0.5
    if {$side eq "0"} { set ip "cw_i\[$b\]"; set op "pin0_q\[$b\]" } else { set ip "ccw_i\[$b\]"; set op "pin1_q\[$b\]" }
  } elseif {[regexp {^cw_[ab]([01])($|[^0-9])} $nm -> d]} {
    set cls cw; set wt 0.1; set ip [expr {$d eq "0" ? "cw_i\[274\]" : "ccw_i\[274\]"}]; set op "carry_write$d"
  } else { continue }
  set bi [$cm_blk findBTerm $ip]; set bo [$cm_blk findBTerm $op]
  if {$bi eq "NULL" || $bo eq "NULL"} { error "CP_MID: missing port $ip / $op for $nm" }
  lassign [cm_center $bi] x0 y0; lassign [cm_center $bo] x1 y1
  set mx [expr {$x0 + $wt * ($x1 - $x0)}]; set my [expr {$y0 + $wt * ($y1 - $y0)}]
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
  incr cm_n; dict incr cm_cls $cls
}
close $cm_fh
puts "CP_MID fixed $cm_n flops at their pin midpoints ($cm_cls)"
if {[dict get $cm_cls cp] != 560 || [dict get $cm_cls cw] != 4} {
  error "CP_MID: expected cp 560 / cw 4 flops, found $cm_cls (netlist renamed / merged?)"
}
