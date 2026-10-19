# KV-HOST/S2 2026-10-19 (qkd_hr_core_order_s2b): the S2 body proposal's full-width north standard-cell band
# (results/arch/kv_order_s2_body_1019/ROOT_REVIEW.md) as an actual INCLUSIVE placement fence.  Every movable
# standard cell joins the fence group before global placement; non-members (CTS / repair buffers) may go anywhere.
# Sourced by the kit's pre_gpl.tcl BEFORE io_flop_at_pins.tcl FIRMs the pin flops at their faces;
# band_fence_release.tcl (PRE_DETAIL_PLACE) drops the members that the pin hook fixed outside the band, so DPL
# legalises them at their pins instead of pulling them into the fence.
set ot_bf_blk [ord::get_db_block]
set ot_bf_dbu [$ot_bf_blk getDbUnitsPerMicron]
set ot_bf_lo 190.08
set ot_bf_hi 265.68
set ot_bf_die [$ot_bf_blk getDieArea]
set ot_bf_x1 [expr {[$ot_bf_die xMax] - round(2.16 * $ot_bf_dbu)}]
set ot_bf_r [odb::dbRegion_create $ot_bf_blk s2_north_band]
$ot_bf_r setRegionType INCLUSIVE
odb::dbBox_create $ot_bf_r [expr {round(2.16 * $ot_bf_dbu)}] [expr {round($ot_bf_lo * $ot_bf_dbu)}] $ot_bf_x1 [expr {round($ot_bf_hi * $ot_bf_dbu)}]
set ot_bf_g [odb::dbGroup_create $ot_bf_blk s2_north_band]
$ot_bf_r addGroup $ot_bf_g
set ot_bf_n 0
foreach i [$ot_bf_blk getInsts] {
  set m [$i getMaster]
  if {[$m isBlock] || [$i isFixed]} continue
  if {[$m getType] ne "CORE"} continue
  $ot_bf_g addInst $i
  incr ot_bf_n
}
if {$ot_bf_n == 0} { error "S2B band fence: no movable core cells" }
puts "S2B_BAND_FENCE members=$ot_bf_n y=$ot_bf_lo..$ot_bf_hi"
