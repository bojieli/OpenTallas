# ELEM-GAPS/HBMN1 r2 PRE_DETAIL_PLACE: release the flops fixed by cp_mid.tcl (ring copies, rr_d, carry_write) so DPL legalises them in place.
set cm_blk [ord::get_db_block]
set cm_n 0
set cm_fh [open $::env(RESULTS_DIR)/ot_cp_mid.txt r]
foreach n [split [read $cm_fh] "\n"] {
  if {$n eq ""} continue
  set i [$cm_blk findInst $n]
  if {$i eq "NULL" || $i eq ""} continue
  $i setPlacementStatus PLACED
  incr cm_n
}
close $cm_fh
puts "CP_MID released $cm_n midpoint flops for DPL"
