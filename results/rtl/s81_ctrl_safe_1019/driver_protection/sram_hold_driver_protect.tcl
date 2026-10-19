# Targeted CTRL diagnosis: keep the HB->driver link and every original hold
# protection intact. OpenDB cannot resize/reconnect a driver input on a protected
# net; downstream driver->capture nets remain available to timing repair.
set ot_cp_block [ord::get_db_block]
set ot_cp_count 0
set ot_cp_expected [expr {[info exists ::env(OT_CTRL_DRIVER_EXPECT)] ? $::env(OT_CTRL_DRIVER_EXPECT) : 1243}]
foreach ot_cp_i [$ot_cp_block getInsts] {
  if {![regexp {^ot_ihdrv_([0-9]{5})$} [$ot_cp_i getName] -> ot_cp_id]} {continue}
  set ot_cp_hb [$ot_cp_block findInst ot_inhold_$ot_cp_id]
  if {$ot_cp_hb eq "NULL" || ![$ot_cp_hb isDoNotTouch]} {error "CTRL_DRV missing/protection-lost hold cell $ot_cp_id"}
  if {[[$ot_cp_i getMaster] getName] ne "BUFx4f_ASAP7_75t_R"} {error "CTRL_DRV unexpected driver master $ot_cp_id"}
  set ot_cp_in [[$ot_cp_i findITerm A] getNet]
  set ot_cp_out [[$ot_cp_i findITerm Y] getNet]
  set ot_cp_port [[$ot_cp_hb findITerm A] getNet]
  if {$ot_cp_in eq "NULL" || [$ot_cp_in getName] ne "ot_inhold_n$ot_cp_id" || ![$ot_cp_in isDoNotTouch]} {error "CTRL_DRV protected HB driver link absent $ot_cp_id"}
  if {[[$ot_cp_hb findITerm Y] getNet] ne $ot_cp_in || ![$ot_cp_port isDoNotTouch]} {error "CTRL_DRV original hold chain changed $ot_cp_id"}
  if {$ot_cp_out eq "NULL" || [$ot_cp_out getName] ne "ot_ihdrv_n$ot_cp_id" || [$ot_cp_out isDoNotTouch]} {error "CTRL_DRV downstream repair no longer available $ot_cp_id"}
  $ot_cp_i setDoNotTouch 1
  incr ot_cp_count
}
if {$ot_cp_count != $ot_cp_expected || $ot_cp_count < 1} {error "CTRL_DRV exact driver count $ot_cp_count != $ot_cp_expected"}
puts "CTRL_DRV_PROTECT_PASS $ot_cp_count exact drivers; HB/port/link protection retained; downstream repair retained"
