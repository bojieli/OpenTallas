# One connected full-width region. Bounds are row-aligned (0.27 um rows).
# Macro/firm boundary cells remain outside the group; every other soft cell
# belongs to the same FENCE, rather than separated macro-gap islands.
set ot_bw_block [ord::get_db_block]
set ot_bw_dbu [$ot_bw_block getDbUnitsPerMicron]
set ot_bw_region [$ot_bw_block findRegion bw_safe3_core_band]
if {$ot_bw_region eq "NULL"} {
  set ot_bw_region [odb::dbRegion_create $ot_bw_block bw_safe3_core_band]
  $ot_bw_region setRegionType EXCLUSIVE
  odb::dbBox_create $ot_bw_region [expr {int(round(2.16*$ot_bw_dbu))}] [expr {int(round(270.0*$ot_bw_dbu))}] [expr {int(round(429.84*$ot_bw_dbu))}] [expr {int(round(291.06*$ot_bw_dbu))}]
}
set ot_bw_group [$ot_bw_block findGroup bw_safe3_core_cells]
if {$ot_bw_group eq "NULL"} {
  set ot_bw_group [odb::dbGroup_create $ot_bw_block bw_safe3_core_cells]
  $ot_bw_region addGroup $ot_bw_group
}
set ot_bw_n 0
foreach inst [$ot_bw_block getInsts] {
  if {[[$inst getMaster] isBlock]} continue
  if {[$inst getPlacementStatus] in {FIRM LOCKED COVER}} continue
  if {[info exists ::ot_bw_safe3_boundary] && [dict exists $::ot_bw_safe3_boundary [$inst getName]]} continue
  $ot_bw_group addInst $inst
  incr ot_bw_n
}
if {$ot_bw_n == 0} { error "BW_SAFE3_BAND: no movable core cells" }
puts "BW_SAFE3_BAND: $ot_bw_n soft cells; one FENCE x2.16..429.84 y270..291.06; pin/hold cells excluded"
