# el1011-q-kvd 2026-10-11: ot_nhb_pbst tile: its two ot_sram_1r1w_128x256 macros stacked and centred (20 um between
# them, >= 20 um to every edge; pdata enters on S, sr leaves on N).  R0, FIRM.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ms {}
foreach m [$b getInsts] { if {[[$m getMaster] isBlock]} { lappend ms [$m getName] } }
if {[llength $ms] != 2} { error "qkd_nhb_pbst_place: expected 2 macros, found [llength $ms]" }
set core [$b getCoreArea]
set cx [expr {([$core xMin] + [$core xMax]) / 2.0 / $dbu}]; set cy [expr {([$core yMin] + [$core yMax]) / 2.0 / $dbu}]
set w 94.824; set h 41.064; set gap 10.8
set x [expr {1.08 * round(($cx - $w / 2.0) / 1.08)}]
set y0 [expr {1.08 * round(($cy - $h - $gap / 2.0) / 1.08)}]
set i 0
foreach n [lsort -dictionary $ms] {
  set m [$b findInst $n]; set y [expr {$y0 + $i * 1.08 * ceil(($h + $gap) / 1.08)}]
  $m setOrient R0; $m setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]; $m setPlacementStatus FIRM
  puts "qkd_nhb_pbst_place: $n at $x $y"; incr i
}
