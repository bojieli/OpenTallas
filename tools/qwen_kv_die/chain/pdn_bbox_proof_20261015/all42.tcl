read_lef tech.lef
read_lef -library elements.lef
set db [ord::get_db]
set chip [odb::dbChip_create $db [$db getTech]]
set block [odb::dbBlock_create $chip all42]
set n 0
foreach lib [$db getLibs] {
  foreach master [$lib getMasters] {
    set inst [odb::dbInst_create $block $master instance_[incr n]]
    $inst setPlacementStatus FIRM
  }
}
source pdn_bbox_obs.tcl
ot_pdn_bbox::begin [pwd]
ot_pdn_bbox::restore
puts "ALL_CASE_MASTER_PIN_OBS_CHECK_PASS masters=$n"
