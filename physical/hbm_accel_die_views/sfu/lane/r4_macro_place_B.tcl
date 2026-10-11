# el1011-hbm-sfu 2026-10-11: RING 4 lane SRAM plan B (r4m160 0e9725b58 GRT-0116: auto placement put both
# ot_sram_1rw_64x128_m1 in the bottom-right corner against the core edge; 395 M4 pins a macro on its L/R edges had no
# channel).  Explicit placement with >= 19 um channels on both pin edges; site / row grid.
set ot_m {}
foreach i [[ord::get_db_block] getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1rw_64x128_m1"} { lappend ot_m $i } }
set ot_m [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $ot_m]
if {[llength $ot_m] != 2} { error "r4_macro_place: expected 2 SRAM macros, found [llength $ot_m]" }
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
foreach i $ot_m {x y} {40.5 155.25 100.44 155.25} {
  $i setOrient R0; $i setOrigin [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]; $i setPlacementStatus FIRM
  puts "r4_macro_place: [$i getName] at ($x $y)"
}
