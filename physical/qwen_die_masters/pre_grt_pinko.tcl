# el1011-q-kvd 2026-10-11 (PINKO=1 in jobs/route_master.sh): hard-tile pin-access keepout.  A parent route of hardened
# tiles died in pin access (qkd_d2d_h-305021c34 / -04612c41b: DRT-0073 u_rb/rst_n of ot_qkvd_sbuf): the tile routed
# its own M5 jog 12 nm beside the 84 nm M4 pin stub, so the parent had no up-via and only a phase-dependent planar
# access.  Before the tile's global route every signal pin gets an M3 + M5 obstruction from its edge 0.60 um inward
# (+-0.06 um about the pin centre) so the tile routes nothing over its own stubs; post_drt_pinko.tcl deletes them
# after detail route so the exported abstract shows the gap (recipe: physical/hbm_accel_die_views/su/lane_pin_keepout_*).
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
set ko_block [ord::get_db_block]
set ko_tech [ord::get_db_tech]
set ko_dbu [$ko_block getDbUnitsPerMicron]
set ko_d [expr {int(0.60 * $ko_dbu)}]
set ko_h [expr {int(0.06 * $ko_dbu)}]
set ko_die [$ko_block getDieArea]
set ko_n 0
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
      foreach ln {M3 M5} { odb::dbObstruction_create $ko_block [$ko_tech findLayer $ln] {*}$bx; incr ko_n }
    }
  }
}
puts "ot tile_pin_keepout: $ko_n M3/M5 obstructions beside signal pins"
