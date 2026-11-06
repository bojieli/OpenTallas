# S81-BKSEL-RF vB (PRE_DETAIL_PLACE): release bank_regs.tcl registers to PLACED, then the kit's face-flop release.
set br_blk [ord::get_db_block]
set br_m 0
set fh [open $::env(RESULTS_DIR)/ot_bank_regs.txt r]
foreach n [split [read $fh] "\n"] {
  if {$n eq ""} continue
  set i [$br_blk findInst $n]
  if {$i ne "NULL" && $i ne "" && [$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED; incr br_m }
}
close $fh
puts "OT_BANK_REGS released $br_m registers for DPL"
source /work/face_flops_release.tcl
