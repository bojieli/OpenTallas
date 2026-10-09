# PRE_DETAIL_PLACE hook (safe-hbm 2026-10-08, R-b): release the IO pin flops fixed by io_flop_at_pins.tcl back to PLACED
# so detailed_placement legalises them next to their pins.
set ot_blk [ord::get_db_block]
set ot_f $::env(RESULTS_DIR)/ot_io_flop_at_pins.txt
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
puts "OT_IOF released $ot_n IO pin flops for DPL"
