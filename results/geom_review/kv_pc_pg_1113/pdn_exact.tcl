read_db /out/parent/2_3_floorplan_tapcell.odb
read_lef /out/qkd_kvs_pcc_h_head_p_EXACT1113.lef
set block [ord::get_db_block]
set inst [$block findInst u_bound.u_kvpc0]
set old [$inst getMaster]
puts "OLD_MASTER=[$old getName]"
if {[$old getName] ne "qkd_kvs_pcc_h_head_p"} {error "Unexpected control master"}
set replacement [[ord::get_db] findMaster qkd_kvs_pcc_h_head_p_EXACT1113]
if {$replacement eq "NULL"} {error "Replacement master absent"}
if {![$inst swapMaster $replacement]} {error "Exact ABI swap failed"}
source /out/parent/pdn_target.tcl
pdngen
write_db /out/PDN_EXACT_ONE_TARGET.odb
exit
