# hardcore-1010 D (2026-10-10): the two program-store SRAMs of ot_qfd_seq_su_bi PSRAM=1 (u_pm of g_psram.g_m[0/1]),
# centred in x, stacked mid-die with a 21.6 um channel between them (>= 12 um: no sliver), >= 100 um off every pin edge.
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set W [expr {double([$die xMax]) / $dbu}]
set H [expr {double([$die yMax]) / $dbu}]
# macro 171.288 x 77.760; x on the 0.216 um grid, y on the 0.270 um (row pair) grid
set x [expr {floor(($W - 171.288) / 2.0 / 0.216) * 0.216}]
set y0 [expr {floor(($H - 2 * 77.76 - 21.6) / 2.0 / 0.27) * 0.27}]
set ms {}
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { lappend ms [$i getName] } }
set ms [lsort $ms]
if {[llength $ms] != 2} { error "seq_su_psram_place requires exactly two SRAMs: [llength $ms]" }
place_macro -macro_name [lindex $ms 0] -location [list $x $y0] -orientation R0
place_macro -macro_name [lindex $ms 1] -location [list $x [expr {$y0 + 77.76 + 21.6}]] -orientation R0
