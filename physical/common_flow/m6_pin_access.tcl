# M6 pin-access stubs for an M5-capped leaf with a named M6 pin grant (Q-XSLEAF 2026-10-16, Q-COMPUTE-DIE option 1).
# Why: with routing layers M2-M5 the detailed router cannot index the V5 access via of an M6 face pin
# (qfd_xs_leaf_w130-w1 5_2: 153x "initMazeIdx_connFig via no idx (x, y) V5", Signal 6).  The kit therefore routes
# signals M2-M6 and this hook confines M6 to the E/W pin-access stubs:
#   PRE_GLOBAL_ROUTE: one M6 routing obstruction over the whole die except the outer ::ot_m6_stub_um at the W and E
#                     faces; every E/W M6 BPin is deepened (same centre, same width) to the stub depth, so all routed
#                     M6 metal sits inside the pin rectangle (the M6 grant's max_depth/max_area still bound it).
#   POST_DETAIL_ROUTE: the same file removes exactly that obstruction again (the abstract carries only real metal; the
#                     parent straps M6 over the tile).
# Probe on the w130 gate CTS db (ot-agidock128): stub 0.384 um and 1.0 um both GRT 0 overflow, DRT 0 violations.
set m6pa_blk [ord::get_db_block]
set m6pa_tech [ord::get_db_tech]
set m6pa_u [$m6pa_blk getDbUnitsPerMicron]
set m6pa_die [$m6pa_blk getDieArea]
set m6pa_l [$m6pa_tech findLayer M6]
set m6pa_s [expr {round($::ot_m6_stub_um * $m6pa_u)}]
set m6pa_r [list [expr {[$m6pa_die xMin] + $m6pa_s}] [$m6pa_die yMin] [expr {[$m6pa_die xMax] - $m6pa_s}] [$m6pa_die yMax]]
set m6pa_have {}
foreach o [$m6pa_blk getObstructions] {
  set bx [$o getBBox]
  if {[[$bx getTechLayer] getName] eq "M6" && [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]] eq $m6pa_r} { lappend m6pa_have $o }
}
if {[llength $m6pa_have]} {
  foreach o $m6pa_have { odb::dbObstruction_destroy $o }
  puts "OT_M6_PIN_ACCESS removed [llength $m6pa_have] M6 obstruction(s)"
} else {
  odb::dbObstruction_create $m6pa_blk $m6pa_l {*}$m6pa_r
  set m6pa_n 0
  foreach bt [$m6pa_blk getBTerms] {
    if {[$bt getSigType] in {POWER GROUND}} continue
    foreach bp [$bt getBPins] {
      foreach bx [$bp getBoxes] {
        if {[[$bx getTechLayer] getName] ne "M6"} continue
        set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
        if {$x0 <= [$m6pa_die xMin]} { set nx0 $x0; set nx1 [expr {$x0 + $m6pa_s}]
        } elseif {$x1 >= [$m6pa_die xMax]} { set nx1 $x1; set nx0 [expr {$x1 - $m6pa_s}]
        } else { error "OT_M6_PIN_ACCESS M6 pin [$bt getName] is not on the W/E face" }
        if {$x1 - $x0 >= $m6pa_s} continue
        odb::dbBox_destroy $bx
        odb::dbBox_create $bp $m6pa_l $nx0 $y0 $nx1 $y1
        incr m6pa_n
      }
    }
  }
  puts "OT_M6_PIN_ACCESS created M6 obstruction $m6pa_r; deepened $m6pa_n E/W M6 pins to $::ot_m6_stub_um um"
}
