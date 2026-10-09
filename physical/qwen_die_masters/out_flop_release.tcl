# PRE_DETAIL_PLACE hook (safe-qwen 2026-10-08): release the output-port flops fixed by out_flop_at_pins.tcl
# (PRE_GLOBAL_PLACE) back to PLACED so detailed_placement legalises them next to their pins.
set ot_blk [ord::get_db_block]
set ot_f $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt
set ot_n 0
if {[file exists $ot_f]} {
  set fh [open $ot_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_n
  }
  close $fh
}
puts "OT_OFLOP released $ot_n output-port flops for DPL"
