# Removal half of post_drt_pinko.tcl (no post_plain): route_master.sh chains it before post_plain.tcl (el1011-rm-pkfix).
# el1011-q-kvd 2026-10-11 (PINKO=1): remove the pre_grt_pinko.tcl keepouts after detail route, then the plain boundary.
set ko_block [ord::get_db_block]
set ko_dbu [$ko_block getDbUnitsPerMicron]
set ko_d [expr {int(0.60 * $ko_dbu)}]
set ko_w [expr {2 * int(0.06 * $ko_dbu)}]
set ko_n 0
foreach ko_ob [$ko_block getObstructions] {
  set b [$ko_ob getBBox]; set ln [[$b getTechLayer] getName]
  set dx [expr {[$b xMax] - [$b xMin]}]; set dy [expr {[$b yMax] - [$b yMin]}]
  if {[lsearch {M3 M4 M5 M6 M7} $ln] >= 0 && (($dx == $ko_d && $dy == $ko_w) || ($dx == $ko_w && $dy == $ko_d))} { odb::dbObstruction_destroy $ko_ob; incr ko_n }
}
puts "ot tile_pin_keepout: removed $ko_n"
