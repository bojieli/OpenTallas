# PRE_DETAIL_PLACE hook (STW-S81c-COLLA2-TX 2026-10-22): release the macro-pin flops fixed by macro_pin_flops.tcl
# (PRE_GLOBAL_PLACE) back to PLACED so detailed_placement legalises them at their pin sites.
set ot_mpf_blk [ord::get_db_block]
set ot_mpf_f $::env(RESULTS_DIR)/ot_macro_pin_flops.txt
set ot_mpf_n 0
if {[file exists $ot_mpf_f]} {
  set fh [open $ot_mpf_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_mpf_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_mpf_n
  }
  close $fh
}
puts "OT_MPF released $ot_mpf_n macro-pin flops for DPL"
