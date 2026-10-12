# el1011-q-kvd 2026-10-11: attention-hub cluster.  Data flow S (pi_* / si_* pins) -> N (out_*).  Row 1 (S): the 4
# beat-store tiles g_s[*].u_pbst (pdata straight up from the S pins).  Row 2: the 4 P.V lane-group tiles g_pv[*].u_pv
# (the sr relay band sits in the channel between rows 1 and 2).  Row 3 (N): the 4 Z head tiles g_zh[*].u_zh, with the
# parent's max / Z control / reciprocal in the centre band between rows 2 and 3 and the out_* registers in the N band.
# Tile size is read from the master (a- or b-variant views); 21.6 um between tiles, 43.2 um bands; R0, FIRM.
# Hard-child origins snap to 8.64 um = lcm of the M2-M7 track pitches (36/48/64 nm), the 54 nm site and the 270 nm row:
# a tile placed on a 1.08 um grid put half its pins off the parent routing grid (qkd_d2d_h-305021c34: DRT-0418 x1000+,
# DRT-0073 no access point).
set ::G 8.64
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set core [$b getCoreArea]
set cx0 [expr {[$core xMin] / double($dbu)}]; set cy0 [expr {[$core yMin] / double($dbu)}]
set cx1 [expr {[$core xMax] / double($dbu)}]; set cy1 [expr {[$core yMax] / double($dbu)}]
array set rows {ot_nhb_pbst {} ot_nhb_pvlg {} ot_nhb_zh {}}
array set wh {}
foreach m [$b getInsts] {
  if {![[$m getMaster] isBlock]} continue
  set mn [[$m getMaster] getName]
  if {![info exists rows($mn)]} { error "qkd_ahub_t_place: unexpected macro $mn" }
  lappend rows($mn) [$m getName]
  set wh($mn) [list [expr {[[$m getMaster] getWidth] / double($dbu)}] [expr {[[$m getMaster] getHeight] / double($dbu)}]]
}
foreach mn {ot_nhb_pbst ot_nhb_pvlg ot_nhb_zh} { if {[llength $rows($mn)] != 4} { error "qkd_ahub_t_place: $mn x[llength $rows($mn)]" } }
set ch 21.6; set band 43.2
set h1 [lindex $wh(ot_nhb_pbst) 1]; set h2 [lindex $wh(ot_nhb_pvlg) 1]; set h3 [lindex $wh(ot_nhb_zh) 1]
set tot [expr {$h1 + $band + $h2 + 2 * $band + $h3}]
set y1 [expr {$::G * round((($cy0 + $cy1) / 2.0 - $tot / 2.0) / $::G)}]
set y2 [expr {$::G * ceil(($y1 + $h1 + $band) / $::G)}]
set y3 [expr {$::G * ceil(($y2 + $h2 + 2 * $band) / $::G)}]
proc row {b dbu names w y cx0 cx1 ch} {
  set k [llength $names]
  set tot [expr {$k * $w + ($k - 1) * $ch}]
  set x [expr {$::G * round((($cx0 + $cx1) / 2.0 - $tot / 2.0) / $::G)}]
  foreach n [lsort -dictionary $names] {
    set m [$b findInst $n]; $m setOrient R0
    $m setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]; $m setPlacementStatus FIRM
    puts "qkd_ahub_t_place: $n at $x $y"; set x [expr {$x + $::G * ceil(($w + $ch) / $::G)}]
  }
}
row $b $dbu $rows(ot_nhb_pbst) [lindex $wh(ot_nhb_pbst) 0] $y1 $cx0 $cx1 $ch
row $b $dbu $rows(ot_nhb_pvlg) [lindex $wh(ot_nhb_pvlg) 0] $y2 $cx0 $cx1 $ch
row $b $dbu $rows(ot_nhb_zh)   [lindex $wh(ot_nhb_zh) 0]   $y3 $cx0 $cx1 $ch
