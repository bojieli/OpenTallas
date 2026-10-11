# el1011-q-kvd 2026-10-11: ot_qkvd_sbuf tile: its one ot_sram_1r1w_64x512 macro centred (>= 33 um to every edge: the
# din (S) and dout (N) pin faces keep a full standard-cell band for the pin flops / head-queue slices).  R0, FIRM.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ms {}
foreach m [$b getInsts] { if {[[$m getMaster] isBlock]} { lappend ms $m } }
if {[llength $ms] != 1} { error "qkd_sbuf_place: expected 1 macro, found [llength $ms]" }
set core [$b getCoreArea]
set cx [expr {([$core xMin] + [$core xMax]) / 2.0 / $dbu}]; set cy [expr {([$core yMin] + [$core yMax]) / 2.0 / $dbu}]
set x [expr {1.08 * round(($cx - 171.288 / 2.0) / 1.08)}]; set y [expr {1.08 * round(($cy - 77.784 / 2.0) / 1.08)}]
set m [lindex $ms 0]; $m setOrient R0; $m setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]; $m setPlacementStatus FIRM
puts "qkd_sbuf_place: [$m getName] at $x $y"
