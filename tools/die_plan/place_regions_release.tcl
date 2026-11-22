# place_regions_release.tcl -- PRE_DETAIL_PLACE (PLACE-GROUP, FABLE-FIX-CONE-SCATTER 11-22, class LOCAL-CONE-SCATTER): a place_regions row
# with kind soft steers global placement only.  Here, after place_regions_inherit.tcl and before DPL, its dbRegion ot_region_<name> and
# its groups are destroyed (members released, they stay where GPL put them), so DPL, repair, CTS and route run free (the S81-DIE-R5
# 11-20 serdes form: a GPL-only region passed DPL where the fence hit DPL-0033).  kind fence rows (default) are untouched.
# Sourced from face_flops_release.tcl when the kit has place_regions_data.tcl.  One line per released region: OT_PLACE_REGION_SOFT_RELEASE.
uplevel #0 {
if {[info exists ::ot_place_regions]} {
  set prr_blk [ord::get_db_block]
  foreach prr_row $::ot_place_regions {
    lassign $prr_row prr_name prr_re prr_util prr_x prr_y prr_near prr_kind
    if {$prr_kind ne "soft"} continue
    set prr_r [$prr_blk findRegion ot_region_$prr_name]
    if {$prr_r eq "NULL" || $prr_r eq ""} { puts "OT_PLACE_REGION_SOFT_RELEASE $prr_name: no region (dropped or empty at global place)"; continue }
    set prr_n 0
    foreach prr_g [$prr_r getGroups] {
      foreach prr_i [$prr_g getInsts] { $prr_g removeInst $prr_i; incr prr_n }
      odb::dbGroup_destroy $prr_g
    }
    odb::dbRegion_destroy $prr_r
    puts "OT_PLACE_REGION_SOFT_RELEASE $prr_name: region and group removed before DPL, $prr_n cells released"
  }
}
}
