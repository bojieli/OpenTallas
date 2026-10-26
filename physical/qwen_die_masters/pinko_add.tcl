# Keepout half of pre_grt_pinko.tcl (no boundary SDC): route_master.sh chains it after pre_ref_skew.tcl so PINKO composes
# with OT_RM_PK and a cfg's own PRE_GLOBAL_ROUTE hook (el1011-rm-pkfix 2026-10-11).
# el1011-q-kvd 2026-10-11 (PINKO=1 in jobs/route_master.sh): hard-tile pin-access keepout.  A parent route of hardened
# tiles died in pin access (qkd_d2d_h-305021c34 / -04612c41b: DRT-0073 u_rb/rst_n of ot_qkvd_sbuf): the tile routed
# its own M5 jog 12 nm beside the 84 nm M4 pin stub, so the parent had no up-via and only a phase-dependent planar
# access.  Before the tile's global route every signal pin gets an obstruction on the layer ABOVE its pin layer from its edge 0.60 um inward
# (+-0.06 um about the pin centre) so the tile routes nothing over its own stubs; post_drt_pinko.tcl deletes them
# after detail route so the exported abstract shows the gap (recipe: physical/hbm_accel_die_views/su/lane_pin_keepout_*).
set ko_block [ord::get_db_block]
set ko_tech [ord::get_db_tech]
set ko_dbu [$ko_block getDbUnitsPerMicron]
set ko_d [expr {int(0.60 * $ko_dbu)}]
set ko_h [expr {int(0.06 * $ko_dbu)}]
set ko_die [$ko_block getDieArea]
set ko_n 0
# layers the tile routes on (an obstruction above the top routing layer is pointless)
set ko_route {}
set ko_lo [expr {[info exists ::env(MIN_ROUTING_LAYER)] ? $::env(MIN_ROUTING_LAYER) : "M2"}]
set ko_hi [expr {[info exists ::env(MAX_ROUTING_LAYER)] ? $::env(MAX_ROUTING_LAYER) : "M6"}]
foreach l [[ord::get_db_tech] getLayers] { if {[$l getType] eq "ROUTING" && [$l getRoutingLevel] >= [[$ko_tech findLayer $ko_lo] getRoutingLevel] && [$l getRoutingLevel] <= [[$ko_tech findLayer $ko_hi] getRoutingLevel]} { lappend ko_route [$l getName] } }
foreach ko_bt [$ko_block getBTerms] {
  if {[$ko_bt getSigType] ne "SIGNAL"} { continue }
  foreach ko_bp [$ko_bt getBPins] {
    foreach ko_box [$ko_bp getBoxes] {
      set x0 [$ko_box xMin]; set x1 [$ko_box xMax]; set y0 [$ko_box yMin]; set y1 [$ko_box yMax]
      set xc [expr {($x0 + $x1) / 2}]; set yc [expr {($y0 + $y1) / 2}]
      if {$x0 <= [$ko_die xMin] + 1} {
        set bx [list [$ko_die xMin] [expr {$yc - $ko_h}] [expr {[$ko_die xMin] + $ko_d}] [expr {$yc + $ko_h}]]
      } elseif {$x1 >= [$ko_die xMax] - 1} {
        set bx [list [expr {[$ko_die xMax] - $ko_d}] [expr {$yc - $ko_h}] [$ko_die xMax] [expr {$yc + $ko_h}]]
      } elseif {$y0 <= [$ko_die yMin] + 1} {
        set bx [list [expr {$xc - $ko_h}] [$ko_die yMin] [expr {$xc + $ko_h}] [expr {[$ko_die yMin] + $ko_d}]]
      } else {
        set bx [list [expr {$xc - $ko_h}] [expr {[$ko_die yMax] - $ko_d}] [expr {$xc + $ko_h}] [$ko_die yMax]]
      }
      # ABOVE ONLY (preamble PIN-ACCESS KEEPOUT, main 10-11 ~21:40): clear only the layer above the pin (the side the
      # parent reaches from); the pin's own layer and the layer below stay free for the tile's own access path.
      set pl [[$ko_box getTechLayer] getName]
      set up [dict get {M2 M3 M3 M4 M4 M5 M5 M6 M6 M7 M7 M8} $pl]
      if {[lsearch $ko_route $up] < 0} { continue }
      odb::dbObstruction_create $ko_block [$ko_tech findLayer $up] {*}$bx; incr ko_n
    }
  }
}
puts "ot tile_pin_keepout: $ko_n above-layer obstructions beside signal pins (route layers $ko_route)"
