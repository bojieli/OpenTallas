# KV-HOST/S2 2026-10-19 (qkd_hr_core_order_s2b, PRE_DETAIL_PLACE after out_flop_release.tcl): a fence member placed
# outside the band was fixed at its pin face by io_flop_at_pins.tcl; drop it from the fence group so DPL legalises
# it at the pin.  Prints the exact count (these are the face-register cells measured_band_fill reports as outside).
set ot_bf_blk [ord::get_db_block]
set ot_bf_g [$ot_bf_blk findGroup s2_north_band]
if {$ot_bf_g eq "NULL" || $ot_bf_g eq ""} { error "S2B band fence group missing at PRE_DETAIL_PLACE" }
set ot_bf_dbu [$ot_bf_blk getDbUnitsPerMicron]
set ot_bf_lo [expr {round(190.08 * $ot_bf_dbu)}]
set ot_bf_out 0
foreach i [$ot_bf_g getInsts] {
  set bb [$i getBBox]
  if {[$bb yMin] < $ot_bf_lo} { $ot_bf_g removeInst $i; incr ot_bf_out }
}
puts "S2B_BAND_FENCE_RELEASE face_cells_outside=$ot_bf_out members_left=[llength [$ot_bf_g getInsts]]"
