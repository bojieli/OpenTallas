# PRE_DETAIL_PLACE hook (vm8 r11): return the input hold cell + driver pairs that leaf_inhold.tcl held FIRM at their
# pins through global placement to PLACED, so detailed_placement legalises them next to their pins.
set ot_blk [ord::get_db_block]
set ot_f $::env(RESULTS_DIR)/ot_inhold_firm.txt
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
puts "INHOLD released $ot_n FIRM hold cells / drivers for DPL"
