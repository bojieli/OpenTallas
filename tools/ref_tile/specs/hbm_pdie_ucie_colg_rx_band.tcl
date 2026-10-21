# UCIE5 rx boundary bank: dedicated enlarged N strip, ordinary legal placement.
set ot_ub [ord::get_db_block]
set ot_ud [$ot_ub getDbUnitsPerMicron]
set ot_ur [odb::dbRegion_create $ot_ub ucie5_rx_face]
$ot_ur setRegionType EXCLUSIVE
odb::dbBox_create $ot_ur [expr {round(5.4*$ot_ud)}] [expr {round(1771.2*$ot_ud)}] [expr {round(129.6*$ot_ud)}] [expr {round(1809.0*$ot_ud)}]
set ot_ug [odb::dbGroup_create $ot_ur ucie5_rx_face]
set ot_un 0
foreach ot_ui [$ot_ub getInsts] {
 if {[string match {u_lpo_rx.q*} [$ot_ui getName]]} { $ot_ug addInst $ot_ui; incr ot_un }
}
if {$ot_un != 513} {error "UCIE5 expected513 rx face flops, found $ot_un"}
puts "UCIE5_RX_BAND $ot_un flops in N43.2um strip; exclusive, retained through DPL/CTS"
