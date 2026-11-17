# S81-COL-SSTN-M5 11-17 (FABLE-PD-S81-0720 B3, COORD): an M5 routing block over the interior of every ot_s81_sstn_* core, created at
# floorplan/pre-GPL time (opt-in OT_S81_SSTN_M5_BLOCK=1, sourced at the end of face_flops.tcl) so the FIRST route never lays M5 wires
# through the core.  Why: the sstn abstract holds its M5 as 817 separate rectangles, so GRT sees free M5 tracks between them that detail
# route cannot use (col pg3: 2 M5 shorts of net155735 against u_u_t6; a post-route block over a routed DB then made 49 more).
# Inset OT_S81_SSTN_M5_INSET_X_UM (default 4.0) / _Y_UM (default 2.0) so pin access at the core edge is untouched.  Routing
# obstruction only: no cell, pin, clock, reset, cycle change.  Idempotent (an identical obstruction is not added twice).
proc ot_sstn_m5_block {} {
  set blk [ord::get_db_block]
  set tech [ord::get_db_tech]
  set dbu [$tech getDbUnitsPerMicron]
  set ix [expr {round($dbu * [expr {[info exists ::env(OT_S81_SSTN_M5_INSET_X_UM)] && $::env(OT_S81_SSTN_M5_INSET_X_UM) ne "" ? $::env(OT_S81_SSTN_M5_INSET_X_UM) : 4.0}])}]
  set iy [expr {round($dbu * [expr {[info exists ::env(OT_S81_SSTN_M5_INSET_Y_UM)] && $::env(OT_S81_SSTN_M5_INSET_Y_UM) ne "" ? $::env(OT_S81_SSTN_M5_INSET_Y_UM) : 2.0}])}]
  set ly [$tech findLayer M5]
  if {$ly eq "NULL"} { error "OT_SSTN_M5_BLOCK no M5 layer" }
  set have [dict create]
  foreach o [$blk getObstructions] {
    set b [$o getBBox]
    if {[[$b getTechLayer] getName] eq "M5"} { dict set have "[$b xMin] [$b yMin] [$b xMax] [$b yMax]" 1 }
  }
  set n 0; set cores 0
  foreach i [$blk getInsts] {
    set mn [[$i getMaster] getName]
    if {![string match "ot_s81_sstn_*" $mn]} continue
    incr cores
    set b [$i getBBox]
    set x0 [expr {[$b xMin] + $ix}]; set y0 [expr {[$b yMin] + $iy}]
    set x1 [expr {[$b xMax] - $ix}]; set y1 [expr {[$b yMax] - $iy}]
    if {$x1 <= $x0 || $y1 <= $y0} { puts "OT_SSTN_M5_BLOCK skip [$i getName]: inset leaves no interior"; continue }
    if {[dict exists $have "$x0 $y0 $x1 $y1"]} continue
    odb::dbObstruction_create $blk $ly $x0 $y0 $x1 $y1
    incr n
    puts [format "OT_SSTN_M5_BLOCK %s %s M5 %.3f %.3f %.3f %.3f" [$i getName] $mn [expr {double($x0)/$dbu}] [expr {double($y0)/$dbu}] [expr {double($x1)/$dbu}] [expr {double($y1)/$dbu}]]
  }
  puts "OT_SSTN_M5_BLOCK done: $n obstructions over $cores ot_s81_sstn_* cores"
}
ot_sstn_m5_block
