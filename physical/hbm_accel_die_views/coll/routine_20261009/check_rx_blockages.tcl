read_db $::env(OT_FAILED_ODB)
if {[catch {source /inspect/rx_macro_blockages.tcl} ot_rx_error]} {
 puts stderr "RX_BLOCKAGE_REJECTED $ot_rx_error"
 exit 1
}
puts "RX_BLOCKAGE_POSITIVE_PASS"
exit 0
