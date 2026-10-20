read_db /case/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_cdc_pc_sram_asap7_ref_gate/base/3_5_place_dp-failed.odb
set b [ord::get_db_block]
set r [$b findRegion ot_pc_band_sram1j]
set g [$b findGroup ot_pc_band_sram1j_group]
set members [$g getInsts]
odb::dbGroup_destroy $g
odb::dbRegion_destroy $r
set r [odb::dbRegion_create $b disjoint_rebuild]
foreach rect {{2160 216000 473040 334800} {226800 2160 253800 216000} {226800 334800 253800 537840}} { odb::dbBox_create $r {*}$rect }
$r setRegionType INCLUSIVE
set g [odb::dbGroup_create $r disjoint_rebuild_group]
foreach i $members {$g addInst $i}
puts "REGION_REBUILD members=[llength $members] boxes=[llength [$r getBoundaries]]"
check_placement
puts "DISJOINT_REBUILD_CHECK PASS"
