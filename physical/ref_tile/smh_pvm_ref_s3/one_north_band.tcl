# Keep one full-width north logic band. Tapcell already ran before this hook.
# LH-COLLPVM 10-19: the rows below the band are KEPT and covered by one HARD placement blockage (core width,
# core yMin .. 229.23 um).  place6 destroyed those rows and detailed placement then crashed
# ("vector range_check 859 >= 264": DPL indexes rows from the core origin, 264 rows were left).
# Physical CORE_WELLTAP / endcap cells under the blockage are still removed (a fixed cell under a hard
# blockage fails DPL, DPL-0033); functional cells and macros are never selected by this cleanup.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cutoff [expr {round(229.23 * $dbu)}]
set ntap 0
foreach inst [$b getInsts] {
  set master [$inst getMaster]
  if {[$master getType] in {CORE_WELLTAP ENDCAP}} {
    set bb [$inst getBBox]
    if {[$bb yMax] <= $cutoff} { odb::dbInst_destroy $inst; incr ntap }
  }
}
set core [$b getCoreArea]
set n 0
foreach row [$b getRows] { if {[[$row getBBox] yMax] <= $cutoff} { incr n } }
set blk [odb::dbBlockage_create $b [$core xMin] [$core yMin] [$core xMax] $cutoff]
if {[$blk isSoft]} { error "PVM_SAFE3: placement blockage is soft" }
puts "PVM_SAFE3 one north logic band y>=229.23um; kept $n lower rows under one HARD placement blockage ([expr {[$core xMin]/double($dbu)}],[expr {[$core yMin]/double($dbu)}])-([expr {[$core xMax]/double($dbu)}],229.23); removed $ntap physical welltaps"
