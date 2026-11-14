# PRIVATE GF5 early-GPL guides end here; no FF-only relocation or timing edit.
set gf5_release_block [ord::get_db_block]
set gf5_release_count 0
foreach gf5_release_region [$gf5_release_block getRegions] {
 if {![string match ot_gf5_* [$gf5_release_region getName]]} continue
 foreach gf5_release_group [$gf5_release_region getGroups] {
  foreach gf5_release_inst [$gf5_release_group getInsts] {$gf5_release_group removeInst $gf5_release_inst}
  odb::dbGroup_destroy $gf5_release_group
 }
 odb::dbRegion_destroy $gf5_release_region
 incr gf5_release_count
}
puts "GF5_LOCALITY released $gf5_release_count guide regions before DPL"
