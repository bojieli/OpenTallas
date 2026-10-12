# el1011-hbm-sfu 10-11 LANE CLUSTER floorplan (159.84 x 330.48, the lane contract): the hard sigmoid chain
# ot_hdc_v41x_sfu_chain (97.2 x 270, pins on its W face toward the lane logic) at (45.36, 8.64): a 45-um lane-logic
# column between the lane's W-face pins and the chain's pins (every seam signal registered on both sides, <= ~60 um),
# 17.3-um E channel; the two RING-4 SRAMs (34.56 x 20.52, M4 pins on L/R) side by side in the 51-um N strip at
# y 293.76 (channels 21.6 / 43.2 / 25.9 um).  Every origin on the 2.16-um M4 / row grid.
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
proc ot_lc_place {inst x y} {
  global dbu
  if {abs(round($y / 2.16) * 2.16 - $y) > 1e-6} { error "r4c_macro_place: y $y off the 2.16-um M4/row grid" }
  $inst setOrient R0; $inst setOrigin [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]; $inst setPlacementStatus FIRM
  puts "r4c_macro_place: [$inst getName] ([[$inst getMaster] getName]) at ($x $y)"
}
set ot_s {}; set ot_c {}
foreach i [[ord::get_db_block] getInsts] {
  set m [[$i getMaster] getName]
  if {$m eq "ot_sram_1rw_64x128_m1"} { lappend ot_s $i }
  if {$m eq "ot_hdc_v41x_sfu_chain"} { lappend ot_c $i }
}
set ot_s [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $ot_s]
if {[llength $ot_s] != 2 || [llength $ot_c] != 1} { error "r4c_macro_place: expected 2 SRAMs + 1 chain, found [llength $ot_s] + [llength $ot_c]" }
ot_lc_place [lindex $ot_c 0] 45.36 8.64
foreach i $ot_s {x y} {21.6 293.76 99.36 293.76} { ot_lc_place $i $x $y }
