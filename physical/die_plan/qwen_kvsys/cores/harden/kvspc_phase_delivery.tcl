# Opt-in boot phase: input capture stays on N, ownership state stays central.
# Region bounds guarantee <=397.44um to every point of the397.44x362.88 lot.
set opd_blk [ord::get_db_block]
set opd_u [$opd_blk getDbUnitsPerMicron]
set opd_inst {}
foreach i [$opd_blk getInsts] {
  if {[regexp {\.u_esm\.own\$} [$i getName]]} {lappend opd_inst $i}
}
if {[llength $opd_inst] != 1} {error "OWN_PHASE_REGION expected exactly one central state FF, got[llength $opd_inst]"}
set opd_reg [$opd_blk findRegion ot_own_phase_centre]
if {$opd_reg eq "NULL"} {
  set opd_reg [odb::dbRegion_create $opd_blk ot_own_phase_centre]
  $opd_reg setRegionType INCLUSIVE
  odb::dbBox_create $opd_reg [expr {round(194.4*$opd_u)}] [expr {round(190.08*$opd_u)}] [expr {round(203.04*$opd_u)}] [expr {round(194.4*$opd_u)}]
  set opd_group [odb::dbGroup_create $opd_reg ot_own_phase_centre]
  $opd_group setType VOLTAGE_DOMAIN
  $opd_group addInst [lindex $opd_inst 0]
}
puts "OWN_PHASE_REGION central state[lindex $opd_inst 0] bbox194.4 190.08 203.04 194.4; boot+1/data+0"
