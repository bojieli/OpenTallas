# el1011-q-kvd 2026-10-11: KV end from hardened buffer tiles.  Data flow S (t_* in / r_* out, sequencer side) -> N
# (tx/rx flits, PHY side).  Row 1 (lowest, next to the S standard-cell band that holds ci_d / r_d): the TX sbuf tiles
# (din from ci_d below, dout up to the N arbiter / tx_flit).  Row 2: the RX sbuf tiles.  Row 3 (next to the N band that
# holds rx_word / tx_flit): the fbuf8 tiles.  21.6 um channels between tiles; R0, FIRM.
# Hard-child origins snap to 8.64 um = lcm of the M2-M7 track pitches (36/48/64 nm), the 54 nm site and the 270 nm row:
# a tile placed on a 1.08 um grid put half its pins off the parent routing grid (qkd_d2d_h-305021c34: DRT-0418 x1000+,
# DRT-0073 no access point).
set ::G 8.64
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set core [$b getCoreArea]
set cx0 [expr {[$core xMin] / double($dbu)}]; set cy0 [expr {[$core yMin] / double($dbu)}]
set cx1 [expr {[$core xMax] / double($dbu)}]; set cy1 [expr {[$core yMax] / double($dbu)}]
set tx {}; set rx {}; set fb {}
foreach m [$b getInsts] {
  if {![[$m getMaster] isBlock]} continue
  set mn [[$m getMaster] getName]; set n [$m getName]
  if {$mn eq "ot_qkvd_sbuf"} { if {[string match "*g_tx*" $n]} { lappend tx $n } else { lappend rx $n } } \
  elseif {$mn eq "ot_qkvd_fbuf8"} { lappend fb $n }
}
set sw 237.6; set sh 151.2; set fw 97.2; set fh 97.2; set ch 21.6
set rowsh [expr {$sh + $ch + $sh + $ch + $fh}]
set y1 [expr {$::G * round((($cy0 + $cy1) / 2.0 - $rowsh / 2.0) / $::G)}]
set y2 [expr {$y1 + $sh + $ch}]; set y3 [expr {$y2 + $sh + $ch}]
proc row {b dbu names w y cx0 cx1 ch} {
  set k [llength $names]; if {$k == 0} return
  set tot [expr {$k * $w + ($k - 1) * $ch}]
  set x [expr {$::G * round((($cx0 + $cx1) / 2.0 - $tot / 2.0) / $::G)}]
  foreach n [lsort -dictionary $names] {
    set m [$b findInst $n]; $m setOrient R0
    $m setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]; $m setPlacementStatus FIRM
    puts "qkd_d2d_h_place: $n at $x $y"; set x [expr {$x + $::G * ceil(($w + $ch) / $::G)}]
  }
}
row $b $dbu $tx $sw $y1 $cx0 $cx1 $ch
row $b $dbu $rx $sw $y2 $cx0 $cx1 $ch
row $b $dbu $fb $fw $y3 $cx0 $cx1 $ch
