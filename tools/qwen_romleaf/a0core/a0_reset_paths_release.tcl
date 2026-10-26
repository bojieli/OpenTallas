set ar_f [open $::env(RESULTS_DIR)/a0_reset_path_flops.txt r]
set ar_blk [ord::get_db_block]
while {[gets $ar_f nm]>=0} {
  set ar_i [$ar_blk findInst $nm]
  if {$ar_i eq "NULL"} {error "OT_A0_RESET_PATH release missing $nm"}
  $ar_i setPlacementStatus PLACED
}
close $ar_f
