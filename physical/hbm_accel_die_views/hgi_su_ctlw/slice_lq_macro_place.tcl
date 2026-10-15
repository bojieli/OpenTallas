# el1011-hbm-sfu 2026-10-11: ot_hgi_su_ctlw_slice LQSRAM - the 8 lanes' landing-FIFO SRAMs (ot_sram_1r1w_64x16_m1,
# 18.36 x 20.79 um) in two rows of four, >= 26 um between macros, >= 20 um to the core edge, 29 um between rows;
# site / row grid.  Explicit (auto placement corner-clustered the lane's SRAMs: r4m160 GRT-0116).
set ot_m {}
foreach i [[ord::get_db_block] getInsts] { if {[[$i getMaster] getName] eq "ot_sram_1r1w_64x16_m1"} { lappend ot_m $i } }
set ot_m [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $ot_m]
if {[llength $ot_m] != 8} { error "slice_lq_macro_place: expected 8 SRAM macros, found [llength $ot_m]" }
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
# 10-11 el1011-hbm-sfu: y on the 2.16-um M4/row grid (submit lint MACRO_GRID: 49.95 / 99.9 put all 63 pins off the M4 tracks)
set xy {15.012 49.68 60.048 49.68 105.03 49.68 150.012 49.68 15.012 99.36 60.048 99.36 105.03 99.36 150.012 99.36}
foreach i $ot_m {x y} $xy {
  $i setOrient R0; $i setOrigin [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]; $i setPlacementStatus FIRM
}
puts "slice_lq_macro_place: 8 SRAMs placed"
