source /src/physical/ha2_truecredit_20261007/rx_capture_pin_release.tcl
set cb [ord::get_db_block]
set fh [open $::env(RESULTS_DIR)/ha2_local_transport_flops.txt r]
foreach name [split [read $fh] "\n"] {
 if {$name eq ""} continue
 set ff [$cb findInst $name]
 if {$ff eq "NULL" || $ff eq ""} {error "Missing modeled transport flop $name"}
 $ff setPlacementStatus PLACED
}
close $fh
