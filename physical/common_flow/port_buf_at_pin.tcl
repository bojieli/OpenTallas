# port_buf_at_pin.tcl (S81-SVCRS-3 11-10, COORD face-side port buffer form). Placement only, 0 cycles, no new cells.
# For every OUTPUT port whose driving cell is a buffer / inverter (the ORFS port buffer or a repair buffer) more than
# OT_PBP_MAX_UM (default 10) from its pin, place that driver just inside the core on the pin's own face, at the pin's
# coordinate along the face, status PLACED, so detailed placement legalises it next to the pin.
# Why: a pass-through register anchored at its INPUT face (skew-line flops of k_key, IRG hslice) launches an output on
# the far face; GPL leaves the port buffer mid-die, so it drives 25-47 um of wire plus set_load 80 fF and the port slew
# reaches 502 ps (limit 260).  repair_design does not split wires shorter than its max wire length (~184 um, ASAP7) and
# leaves these nets alone (61 slew violations found, 0 cells added).  With the buffer at the pin the long wire sits on
# its input side (one gate pin of load), as on the ports that already close (ko_key[300]: buffer 3.5 um from the pin).
# Use: PRE_DETAIL_PLACE (after the pin-flop release) in a kit, or in an ECO session before detailed_placement.
set ot_pbp_blk [ord::get_db_block]
set ot_pbp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_pbp_max [expr {[info exists ::env(OT_PBP_MAX_UM)] ? double($::env(OT_PBP_MAX_UM)) : 10.0}]
set ot_pbp_gap [expr {[info exists ::env(OT_PBP_GAP_UM)] ? double($::env(OT_PBP_GAP_UM)) : 0.5}]
set ot_pbp_pat [expr {[info exists ::env(OT_PBP_MASTERS)] ? $::env(OT_PBP_MASTERS) : {^(BUF|INV|HB)}}]
set ot_pbp_core [$ot_pbp_blk getCoreArea]
set cx0 [$ot_pbp_core xMin]; set cx1 [$ot_pbp_core xMax]; set cy0 [$ot_pbp_core yMin]; set cy1 [$ot_pbp_core yMax]
set ot_pbp_n 0; set ot_pbp_skip 0; set ot_pbp_far 0.0
foreach bt [$ot_pbp_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  if {[$net getSigType] ne "SIGNAL"} continue
  set drv {}
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { lappend drv $it } }
  if {[llength $drv] != 1} { incr ot_pbp_skip; continue }
  set inst [[lindex $drv 0] getInst]
  set m [$inst getMaster]
  if {![regexp $ot_pbp_pat [$m getName]]} { incr ot_pbp_skip; continue }
  if {[$inst getPlacementStatus] in {FIRM LOCKED COVER}} { incr ot_pbp_skip; continue }
  set bb [$bt getBBox]
  set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
  set ib [$inst getBBox]
  set ix [expr {([$ib xMin] + [$ib xMax]) / 2}]; set iy [expr {([$ib yMin] + [$ib yMax]) / 2}]
  set d [expr {(abs($px - $ix) + abs($py - $iy)) / double($ot_pbp_dbu)}]
  if {$d <= $ot_pbp_max} continue
  set w [$m getWidth]; set h [$m getHeight]; set g [expr {int($ot_pbp_gap * $ot_pbp_dbu)}]
  # the face the pin sits on: nearest core edge
  set dl [expr {abs($px - $cx0)}]; set dr [expr {abs($px - $cx1)}]; set db [expr {abs($py - $cy0)}]; set dt [expr {abs($py - $cy1)}]
  set mn [expr {min($dl, $dr, $db, $dt)}]
  if {$mn == $dr} { set x [expr {$cx1 - $w - $g}]; set y [expr {$py - $h / 2}]
  } elseif {$mn == $dl} { set x [expr {$cx0 + $g}]; set y [expr {$py - $h / 2}]
  } elseif {$mn == $dt} { set x [expr {$px - $w / 2}]; set y [expr {$cy1 - $h - $g}]
  } else { set x [expr {$px - $w / 2}]; set y [expr {$cy0 + $g}] }
  set x [expr {max($cx0, min($x, $cx1 - $w))}]; set y [expr {max($cy0, min($y, $cy1 - $h))}]
  $inst setLocation [expr {int($x)}] [expr {int($y)}]
  $inst setPlacementStatus PLACED
  if {$d > $ot_pbp_far} { set ot_pbp_far $d }
  incr ot_pbp_n
  if {[info exists ::env(OT_PBP_VERBOSE)]} { puts "OT_PBP [$bt getName] [$inst getName] [$m getName] moved [format %.1f $d] um" }
}
puts "OT_PBP moved $ot_pbp_n output-port drivers to their pin face (> $ot_pbp_max um; farthest [format %.1f $ot_pbp_far] um); skipped $ot_pbp_skip (not a single BUF/INV/HB driver or fixed)"
