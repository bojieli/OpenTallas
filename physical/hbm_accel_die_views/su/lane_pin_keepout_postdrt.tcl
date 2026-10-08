# hbm-blocks 2026-10-07: remove the lane pin-access keepouts (lane_pin_keepout_pregrt.tcl) after detail route, so the
# exported abstract carries no obstruction there; only M3 / M5 obstructions created by that hook exist in a lane.
set ko_block [ord::get_db_block]
set ko_dbu [$ko_block getDbUnitsPerMicron]
set ko_d [expr {int(0.60 * $ko_dbu)}]
set ko_w [expr {2 * int(0.06 * $ko_dbu)}]
set ko_n 0
foreach ko_ob [$ko_block getObstructions] {
  set b [$ko_ob getBBox]
  set ln [[$b getTechLayer] getName]
  set dx [expr {[$b xMax] - [$b xMin]}]; set dy [expr {[$b yMax] - [$b yMin]}]
  if {($ln eq "M3" || $ln eq "M5") && (($dx == $ko_d && $dy == $ko_w) || ($dx == $ko_w && $dy == $ko_d))} {
    odb::dbObstruction_destroy $ko_ob; incr ko_n
  }
}
puts "ot lane_pin_keepout: removed $ko_n obstructions"
