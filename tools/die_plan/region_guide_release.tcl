# FLOW-23 class D: PRE_DETAIL_PLACE (end of face_flops_release.tcl): remove the region_guide.tcl regions (ot_rg_*) so
# DPL / repair / CTS run free; the registers stay where GPL put them.
uplevel #0 {
set rgr_blk [ord::get_db_block]
set rgr_n 0
foreach r [$rgr_blk getRegions] {
  if {![string match ot_rg_* [$r getName]]} continue
  foreach g [$r getGroups] {
    foreach i [$g getInsts] { $g removeInst $i }
    odb::dbGroup_destroy $g
  }
  odb::dbRegion_destroy $r
  incr rgr_n
}
puts "OT_REGION_GUIDE released $rgr_n guide regions before detailed placement"
}
