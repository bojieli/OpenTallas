# PRE_DETAIL_PLACE hook (HBMc/TILES2 2026-10-22): release the SRAM write-port registers fixed by sram_wport_at_pins.tcl.
set ot_blk [ord::get_db_block]
set ot_f $::env(RESULTS_DIR)/ot_sram_wport_firm.txt
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
puts "OT_SWP released $ot_n SRAM write-port cells for DPL"
