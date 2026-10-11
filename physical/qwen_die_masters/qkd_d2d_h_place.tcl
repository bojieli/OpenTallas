# el1011-q-kvd 2026-10-11: KV end from hardened buffer tiles.  Data flow S (t_* in / r_* out, sequencer side) -> N
# (tx/rx flits, PHY side).  Row 1 (lowest, next to the S standard-cell band that holds ci_d / r_d): the TX sbuf tiles
# (din from ci_d below, dout up to the N arbiter / tx_flit).  Row 2: the RX sbuf tiles.  Row 3 (next to the N band that
# holds rx_word / tx_flit): the fbuf8 tiles.  21.6 um channels between tiles; R0, FIRM.
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
set sw 237.6; set sh 151.2; set fw 81.0; set fh 81.0; set ch 21.6
set rowsh [expr {$sh + $ch + $sh + $ch + $fh}]
set y1 [expr {1.08 * round((($cy0 + $cy1) / 2.0 - $rowsh / 2.0) / 1.08)}]
set y2 [expr {$y1 + $sh + $ch}]; set y3 [expr {$y2 + $sh + $ch}]
proc row {b dbu names w y cx0 cx1 ch} {
  set k [llength $names]; if {$k == 0} return
  set tot [expr {$k * $w + ($k - 1) * $ch}]
  set x [expr {1.08 * round((($cx0 + $cx1) / 2.0 - $tot / 2.0) / 1.08)}]
  foreach n [lsort -dictionary $names] {
    set m [$b findInst $n]; $m setOrient R0
    $m setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]; $m setPlacementStatus FIRM
    puts "qkd_d2d_h_place: $n at $x $y"; set x [expr {$x + 1.08 * ceil(($w + $ch) / 1.08)}]
  }
}
row $b $dbu $tx $sw $y1 $cx0 $cx1 $ch
row $b $dbu $rx $sw $y2 $cx0 $cx1 $ch
row $b $dbu $fb $fw $y3 $cx0 $cx1 $ch
