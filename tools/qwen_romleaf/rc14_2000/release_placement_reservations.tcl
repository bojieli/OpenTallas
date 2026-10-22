# A0 rc14: source ownership shapes GPL; late repair cells need the same real rows.
# No clock, data, hard child, source register or timing constraint is changed.
set a0_block [ord::get_db_block]
set a0_inst_count [llength [$a0_block getInsts]]
set a0_net_count [llength [$a0_block getNets]]
set a0_released 0
foreach a0_group [$a0_block getGroups] {
 if {![string match qrl_* [$a0_group getName]]} {continue}
 set a0_name [$a0_group getName]
 set a0_region [$a0_group getRegion]
 set a0_members [llength [$a0_group getInsts]]
 odb::dbGroup_destroy $a0_group
 if {$a0_region ne "NULL"} {odb::dbRegion_destroy $a0_region}
 incr a0_released
 puts "A0_GPL_OWNERSHIP_RELEASE $a0_name members=$a0_members"
}
if {[llength [$a0_block getInsts]] != $a0_inst_count || [llength [$a0_block getNets]] != $a0_net_count} {
 error "A0 placement reservation release changed physical connectivity"
}
puts "A0_GPL_OWNERSHIP_RELEASE_PASS groups=$a0_released insts=$a0_inst_count nets=$a0_net_count"
