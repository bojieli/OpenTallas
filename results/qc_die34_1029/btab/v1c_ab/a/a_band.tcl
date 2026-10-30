# DIE-QC-36 KITS BTAB QC-014 variant (A): EAST PIN-COLUMN RE-PLACE (GPL only).  Hard placement blockage over the band
# x [261.738, OT_ABAND_X1=264.330] (2.592 um = 48 sites, i.e. the first ~18 M3 tracks east of the g_btb[1]/[3] E
# pin-column strip outer edge) over both macro y-spans (same y as the kit strip blockages), carved around any fixed
# instance, so GPL places the E pin-column cells (DFF / AO22 / BUFx2 hold column at x 261.7-268 in V1c) east of the
# band.  The band blockages are REMOVED again before DPL (a_band_remove), so DPL / CTS / the FIRM plan tree cells are
# unaffected; only the GPL spread moves the column.  Not a check.
proc a_band_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc a_band_create {} {
  set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set x0 [expr round(261.738*$u)]; set x1 [expr round([a_band_env OT_ABAND_X1 264.330]*$u)]
  set n 0
  foreach span {{10.986 64.398} {84.426 137.838}} {
    lassign $span ya yb; set ya [expr round($ya*$u)]; set yb [expr round($yb*$u)]
    set cuts {}
    foreach i [$b getInsts] { if {![$i isFixed]} continue; set bb [$i getBBox]
      if {[$bb xMax] > $x0 && [$bb xMin] < $x1 && [$bb yMax] > $ya && [$bb yMin] < $yb} { lappend cuts [list [$bb yMin] [$bb yMax]] } }
    set cuts [lsort -integer -index 0 $cuts]; set y $ya
    foreach c $cuts { lassign $c c0 c1; if {$c0 > $y} { odb::dbBlockage_create $b $x0 $y $x1 $c0; incr n }; if {$c1 > $y} { set y $c1 } }
    if {$y < $yb} { odb::dbBlockage_create $b $x0 $y $x1 $yb; incr n }
  }
  puts "A_BAND created $n placement blockages x [expr $x0/double($u)]-[expr $x1/double($u)] (fixed cuts carved)"
}
proc a_band_remove {} {
  set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set x0 [expr round(261.738*$u)]; set x1 [expr round([a_band_env OT_ABAND_X1 264.330]*$u)]; set n 0
  foreach bl [$b getBlockages] { set bb [$bl getBBox]; if {[$bb xMin] == $x0 && [$bb xMax] == $x1} { odb::dbBlockage_destroy $bl; incr n } }
  puts "A_BAND removed $n band blockages before DPL"
}
