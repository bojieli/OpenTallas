# Keep vias off the real SRAM M4 east OBS: preserve LEF, signal pins and 20um guards.
# M4 is the pin escape layer. M3/M5 vias may start only after escaping the edge strip.
set eb [ord::get_db_block]
set et [ord::get_db_tech]
set eu [$et getDbUnitsPerMicron]
set en 0
foreach ei [$eb getInsts] {
  if {[[$ei getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} { continue }
  set ex [$ei getBBox]
  set ex0 [expr {[$ex xMax] - round(.144 * $eu)}]
  set ex1 [expr {[$ex xMax] + round(.288 * $eu)}]
  foreach el {M3 M5} {
    odb::dbObstruction_create $eb [$et findLayer $el] $ex0 [$ex yMin] $ex1 [$ex yMax]
    incr en
  }
}
if {$en != 2} { error "IX bank macro escape expected one actual SRAM / two layer obstructions; got $en" }
puts "IX_BANK_MACRO_ESCAPE real SRAM E face: M3/M5 via keepout .144 inside/.288 outside; M4 pin escape unchanged"
