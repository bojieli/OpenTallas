# HBM-CORES-REBAL-10: PRE_DETAIL_PLACE (end of face_flops_release.tcl): remove the macro_reg_guide.tcl regions (ot_mrg_*)
# so DPL legalises freely; the registers stay where GPL put them.
uplevel #0 {
set mrr_blk [ord::get_db_block]
set mrr_n 0
foreach r [$mrr_blk getRegions] {
  if {![string match ot_mrg_* [$r getName]]} continue
  foreach g [$r getGroups] {
    foreach i [$g getInsts] { $g removeInst $i }
    odb::dbGroup_destroy $g
  }
  odb::dbRegion_destroy $r
  incr mrr_n
}
puts "OT_MACRO_REG_GUIDE released $mrr_n guide regions before detailed placement"
}
