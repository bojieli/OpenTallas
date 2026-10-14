read_db /work/routes/gate/work/orfs/results/asap7/opentallas_ot_qwen_tile_ctl_tp8_asap7_ref_gate/base/$::env(CENSUS_STAGE).odb
set nff 0
set types {}
foreach inst [[ord::get_db_block] getInsts] {
 set mn [[$inst getMaster] getName]
 if {![regexp {^(ASYNC_)?(S?DFF|SDF[HL]|DHL|DLL)} $mn]} continue
 incr nff
 dict incr types $mn
}
puts "CENSUS_STAGE $::env(CENSUS_STAGE) FF $nff TYPES $types"
exit
