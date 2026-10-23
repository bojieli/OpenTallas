# PRE_DETAIL_PLACE hook (STEWARD-HBMd/E86 2026-10-23, kit e86rt): release the up_in capture flops fixed by upin_anchor.tcl
# back to PLACED so detailed_placement legalises them beside their S-face pins.
set ur_blk [ord::get_db_block]
set ur_f $::env(RESULTS_DIR)/ot_upin_anchor.txt
set ur_n 0
if {[file exists $ur_f]} {
  set fh [open $ur_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ur_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ur_n
  }
  close $fh
}
puts "UPIN_ANCHOR released $ur_n up_in capture flops for DPL"
