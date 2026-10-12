# 10-11 el1011-hbm-sfu: y on the 2.16-um grid (193869878 r4mpa/b DRT-0255 at the macro with y 182.25 / 155.25: pins off the M4 tracks)
# el1011-hbm-sfu 2026-10-11: RING 4 lane SRAM plan A (r4m160 0e9725b58 GRT-0116: auto placement put both
# ot_sram_1rw_64x128_m1 in the bottom-right corner against the core edge; 395 M4 pins a macro on its L/R edges had no
# channel).  Explicit placement with >= 19 um channels on both pin edges; site / row grid.
set ot_m {}
foreach i [[ord::get_db_block] getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1rw_64x128_m1"} { lappend ot_m $i } }
set ot_m [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $ot_m]
if {[llength $ot_m] != 2} { error "r4_macro_place: expected 2 SRAM macros, found [llength $ot_m]" }
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
foreach i $ot_m {x y} {62.64 140.4 62.64 181.44} {
  # macro M4 pins sit on the M4 track lattice only when y is on 0.048 (and the row grid 0.27): 2.16-um grid
  if {abs(round($y / 2.16) * 2.16 - $y) > 1e-6} { error "r4_macro_place: y $y off the 2.16-um M4/row grid" }
  $i setOrient R0; $i setOrigin [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]; $i setPlacementStatus FIRM
  puts "r4_macro_place: [$i getName] at ($x $y)"
}
