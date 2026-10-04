# --step-tcl POST_PDN hook for the ot_fwd_link_stage 430.56 um span run: fence the stage's capture flops (and
# their D-side logic) at the RECEIVING (east) end, so the 430 um hop is the input wire from the west ports, travelled
# by both the data and the forwarded clock, as in a chain of link stages.  Geometry only; no timing constraint.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set region [odb::dbRegion_create $block "rx_end"]
odb::dbBox_create $region [expr {int(395 * $dbu)}] [expr {int(5 * $dbu)}] [expr {int(445 * $dbu)}] [expr {int(155 * $dbu)}]
set n 0
foreach inst [$block getInsts] {
  if {[[$inst getMaster] isSequential]} { $region addInst $inst; incr n }
}
puts "OT_FENCE rx_end sequential instances: $n"
