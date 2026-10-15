# hbm-blocks 2026-10-07: lane pin-access keepout (PINKO=1 in route_lane.sh).  The quarter's pin access failed on the
# r24 SFU quarter (DRT-0073 u_lane_*/ce_imm1[11], aibase[0]: the lane abstract's M3 / M5 OBS cover the 0.084 um M4 pin
# stubs, so only an on-track planar M4 access remains and some placement phases have none).  Before the lane's global
# route, every signal pin gets an M3 and M5 routing obstruction from its edge 0.60 um inward (+-0.06 um about the pin
# centre), so the lane routes nothing over its own pin stubs; lane_pin_keepout_postdrt.tcl deletes them after detail
# route, so the abstract shows the gap.  Then the karb buffer-cap repair this hook ran before.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
set ko_block [ord::get_db_block]
set ko_tech [ord::get_db_tech]
set ko_dbu [$ko_block getDbUnitsPerMicron]
# [sfu] 10-10: OT_PINKO_LAYERS (default "M3 M5") / OT_PINKO_DEPTH (default 0.60 um).  The hfd_sfu_tile pin-access repro
# (DRT pin_access on the tile's placed db, eco4 lane abstract) shows the parent reaches these M4 stubs by an UP via (V4 to
# M5): removing the M5 OBS beside ce_imm1[11] gave it an access point, trimming the M3 OBS did not.  An M5-only keepout
# keeps the lane's M3 pin escape (the M3+M5 0.60 keepout left 414 lane DRC, all M4 at x < 1 um: b9929dc41).
set ko_layers [expr {[info exists ::env(OT_PINKO_LAYERS)] && $::env(OT_PINKO_LAYERS) ne "" ? $::env(OT_PINKO_LAYERS) : "M3 M5"}]
set ko_depth [expr {[info exists ::env(OT_PINKO_DEPTH)] && $::env(OT_PINKO_DEPTH) ne "" ? $::env(OT_PINKO_DEPTH) : 0.60}]
set ko_d [expr {int($ko_depth * $ko_dbu)}]
set ko_h [expr {int(0.06 * $ko_dbu)}]
set ko_die [$ko_block getDieArea]
set ko_n 0
foreach ko_bt [$ko_block getBTerms] {
  if {[$ko_bt getSigType] ne "SIGNAL"} { continue }
  foreach ko_bp [$ko_bt getBPins] {
    foreach ko_box [$ko_bp getBoxes] {
      set x0 [$ko_box xMin]; set x1 [$ko_box xMax]; set y0 [$ko_box yMin]; set y1 [$ko_box yMax]
      set xc [expr {($x0 + $x1) / 2}]; set yc [expr {($y0 + $y1) / 2}]
      if {$x0 <= [$ko_die xMin] + 1} {            ;# W edge
        set bx [list [$ko_die xMin] [expr {$yc - $ko_h}] [expr {[$ko_die xMin] + $ko_d}] [expr {$yc + $ko_h}]]
      } elseif {$x1 >= [$ko_die xMax] - 1} {      ;# E edge
        set bx [list [expr {[$ko_die xMax] - $ko_d}] [expr {$yc - $ko_h}] [$ko_die xMax] [expr {$yc + $ko_h}]]
      } elseif {$y0 <= [$ko_die yMin] + 1} {      ;# S edge
        set bx [list [expr {$xc - $ko_h}] [$ko_die yMin] [expr {$xc + $ko_h}] [expr {[$ko_die yMin] + $ko_d}]]
      } else {                                    ;# N edge
        set bx [list [expr {$xc - $ko_h}] [expr {[$ko_die yMax] - $ko_d}] [expr {$xc + $ko_h}] [$ko_die yMax]]
      }
      foreach ln $ko_layers {
        set L [$ko_tech findLayer $ln]
        odb::dbObstruction_create $ko_block $L {*}$bx
        incr ko_n
      }
    }
  }
}
puts "ot lane_pin_keepout: $ko_n obstructions ($ko_layers, depth $ko_depth um) beside signal pins"
