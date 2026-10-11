source /src/physical/ha2_truecredit_20261007/rx_capture_release.tcl
source /src/physical/common_flow/io_flop_release.tcl
set cb [ord::get_db_block]
set fh [open $::env(RESULTS_DIR)/ha2_send_pin_flops.txt r]
foreach name [split [read $fh] "\n"] {
 if {$name eq ""} continue
 set ff [$cb findInst $name]
 if {$ff eq "NULL" || $ff eq ""} {error "Missing send_v pin flop $name"}
 $ff setPlacementStatus PLACED
}
close $fh
