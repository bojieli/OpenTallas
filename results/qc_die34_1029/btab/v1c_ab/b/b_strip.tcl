# DIE-QC-36 KITS BTAB QC-014 variant (B), kit hook (PRE_GLOBAL_ROUTE; not a check):
#  (1) M5 obstruction over the g_btb[1]/[3] E pin-face inner strip [252.964, 254.592] (same x as the existing M4+V4
#      keep-off, full macro height).  V1c 6_final (CHECKED, dbWirePathItr probe): the ONLY nets with M5/V4 shapes in these
#      strips are the 2 DRC nets (_1154_, g_btb[0].m_wa[8]); 0 frozen clock nets.  M4 and V4 there were already
#      obstructed, so with M5 gone no wire can enter the strip at all: the V45-dive + M4-exit across the macro M4 OBS
#      (the whole V1c/V1d DRC class) has no legal OR illegal-by-choice entry.  PG M5 stripe 252.564-252.876 is outside.
#  (2) GRT M3 corridor reserve: region adjustment OT_BCOR_ADJ (0.30) on M3 over the E pin-column strip x [254.664,
#      261.738] for both macro y-spans (kit strip blockage y), so global routing leaves DRT 30 % of the corridor's
#      vertical tracks for pin access / the detours it took inside the macro in V1c/V1d.
proc b_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc b_strip {} {
  set b [ord::get_db_block]; set t [ord::get_db_tech]; set u [$t getDbUnitsPerMicron]; set m5 [$t findLayer M5]
  set n 0
  foreach ys {{17.280 58.344} {90.720 131.784}} { lassign $ys y0 y1
    odb::dbObstruction_create $b $m5 [expr round(252.964*$u)] [expr round($y0*$u)] [expr round(254.592*$u)] [expr round($y1*$u)]; incr n }
  set adj [b_env OT_BCOR_ADJ 0.30]
  foreach ys {{10.986 64.398} {84.426 137.838}} { lassign $ys y0 y1
    set_global_routing_region_adjustment [list 254.664 $y0 261.738 $y1] -layer M3 -adjustment $adj }
  puts "B_STRIP $n M5 obstructions (E strips g_btb\[1\]/\[3\]) + M3 corridor region adjustment $adj x 254.664-261.738"
}
b_strip
