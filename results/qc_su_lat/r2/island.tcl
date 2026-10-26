# QC-SU-LAT-R2 (METHODOLOGY 12.2a/12.7c/12.8a): ONE top-owned clock/reset INFRA ISLAND at the master-plan clock entry.
# OT_ISLAND = "x y side" (um, core frame).  Hard placement blockage (die clock drivers + regional reset relay only, placed by
# the die) + M2-M4 routing obstruction (die-owned M1-M4 inside; core signals stay out); M1/M2 follow-pins and the M5 PG
# stripes run through it (island PG rails = core rails).  Core clock pin ck moves to an M5 interior pin at the island
# centre (die M9->M5 via stack lands on it).  Sourced first in PRE_GLOBAL_PLACE.
lassign $::env(OT_ISLAND) ot_ix ot_iy ot_is
set ot_b [ord::get_db_block]; set ot_u [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_h [expr {$ot_is / 2.0}]
set ot_x0 [expr {round(($ot_ix - $ot_h) * $ot_u)}]; set ot_x1 [expr {round(($ot_ix + $ot_h) * $ot_u)}]
set ot_y0 [expr {round(($ot_iy - $ot_h) * $ot_u)}]; set ot_y1 [expr {round(($ot_iy + $ot_h) * $ot_u)}]
if {[llength [$ot_b getBlockages]] == 0 || ![info exists ::ot_island_done]} {
  set ot_bl [odb::dbBlockage_create $ot_b $ot_x0 $ot_y0 $ot_x1 $ot_y1]
  foreach l {M2 M3 M4} { odb::dbObstruction_create $ot_b [[ord::get_db_tech] findLayer $l] $ot_x0 $ot_y0 $ot_x1 $ot_y1 }
  # the core's well-tap column cells inside the hole move to the island owner (die island cells carry their own taps)
  set ot_nt 0
  foreach i [$ot_b getInsts] {
    if {![string match "TAPCELL*" [[$i getMaster] getName]]} continue
    set bb [$i getBBox]
    if {[$bb xMax] > $ot_x0 && [$bb xMin] < $ot_x1 && [$bb yMax] > $ot_y0 && [$bb yMin] < $ot_y1} { odb::dbInst_destroy $i; incr ot_nt }
  }
  puts "OT_ISLAND removed $ot_nt core tapcells inside the island (island owner supplies its well taps)"
  set ::ot_island_done 1
}
set ot_px [expr {[info exists ::env(OT_CK_PIN_X)] ? $::env(OT_CK_PIN_X) : $ot_ix}]
place_pin -pin_name ck -layer M5 -location [list $ot_px $ot_iy] -pin_size {0.024 0.384}
puts [format "OT_ISLAND clock/reset island %.3f x %.3f um at (%.3f, %.3f) rect %.3f %.3f %.3f %.3f: placement blockage + M2-M4 obstruction; ck = M5 interior pin at (%.3f, %.3f)" \
  $ot_is $ot_is $ot_ix $ot_iy [expr {$ot_x0/double($ot_u)}] [expr {$ot_y0/double($ot_u)}] [expr {$ot_x1/double($ot_u)}] [expr {$ot_y1/double($ot_u)}] $ot_px $ot_iy]
