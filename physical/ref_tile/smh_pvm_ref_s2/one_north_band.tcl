# Keep one full-width north logic band. Tapcell already ran before this hook.
# Remove only physical CORE_WELLTAP infrastructure on the rows being removed;
# functional cells and macros are never selected by this cleanup.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cutoff [expr {round(216.0 * $dbu)}]
set ntap 0
foreach inst [$b getInsts] {
  set master [$inst getMaster]
  if {[$master getType] eq "CORE_WELLTAP"} {
    lassign [$inst getLocation] x y
    if {$y < $cutoff} { odb::dbInst_destroy $inst; incr ntap }
  }
}
set n 0
foreach row [$b getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] < $cutoff} { odb::dbRow_destroy $row; incr n }
}
puts "PVM_SAFE2 one north logic band y>=216um; removed $n lower rows and $ntap physical welltaps"
