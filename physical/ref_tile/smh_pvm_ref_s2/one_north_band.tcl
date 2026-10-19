# One full-width north logic band. Remove rows rather than hard-blocking
# tapcell endcaps. Existing fixed tap/endcap infrastructure may remain below.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set n 0
foreach row [$b getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] < round(216.0 * $dbu)} { odb::dbRow_destroy $row; incr n }
}
puts "PVM_SAFE2 one north logic band y>=216um; removed $n lower placement rows"
