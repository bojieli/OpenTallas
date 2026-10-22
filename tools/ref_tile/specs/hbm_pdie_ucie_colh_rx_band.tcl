# UCIE6 colh rx boundary bank: top 43.2 um strip of the 1555.2 outline, ordinary legal placement.
set ot_ub [ord::get_db_block]
set ot_ud [$ot_ub getDbUnitsPerMicron]
set ot_ur [odb::dbRegion_create $ot_ub ucie5_rx_face]
$ot_ur setRegionType EXCLUSIVE
odb::dbBox_create $ot_ur [expr {round(5.4*$ot_ud)}] [expr {round(1512.0*$ot_ud)}] [expr {round(129.6*$ot_ud)}] [expr {round(1549.8*$ot_ud)}]
set ot_ug [odb::dbGroup_create $ot_ur ucie5_rx_face]
set ot_un 0
foreach ot_ui [$ot_ub getInsts] {
 if {[string match {u_lpo_rx.q*} [$ot_ui getName]]} { $ot_ug addInst $ot_ui; incr ot_un }
}
if {$ot_un != 512} {error "UCIE5 expected512 rx face flops, found $ot_un"}
puts "UCIE5_RX_BAND $ot_un flops in N43.2um strip; exclusive, retained through DPL/CTS"
