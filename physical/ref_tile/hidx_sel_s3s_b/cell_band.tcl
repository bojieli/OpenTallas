# A real placement fence: keep the mapped logic in the priced lower cell band.
# No netlist, clock, exception, or timing changes. Macros keep literal lattice origins.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set region [$b findRegion codex_idx_lower_band]
if {$region eq "NULL"} {
  set region [odb::dbRegion_create $b codex_idx_lower_band]
  $region setRegionType EXCLUSIVE
  odb::dbBox_create $region [expr {round(2.16*$dbu)}] [expr {round(2.16*$dbu)}] [expr {round(343.44*$dbu)}] [expr {round(39.96*$dbu)}]
}
set count 0
foreach inst [$b getInsts] {
  set master [$inst getMaster]
  if {[$master isBlock] || [$inst getPlacementStatus] in {FIRM LOCKED COVER}} continue
  $region addInst $inst
  incr count
}
puts "CODEX_IDX_BAND: fenced $count mapped cells in [list 2.16 2.16 343.44 39.96] um"
