# Read-only diagnostic of the preserved failed placement. No design mutation.
if {![info exists ::env(OT_FAILED_ODB)]} {error "OT_FAILED_ODB required"}
read_db $::env(OT_FAILED_ODB)
set block [ord::get_db_block]
puts "CORE [$block getCoreArea] DBU [$block getDbUnitsPerMicron]"
set nr 0
foreach row [$block getRows] {
 if {$nr < 3} {
  set site [$row getSite]
  puts "ROW [$row getName] ORIGIN [$row getOrigin] SITE [$site getName] SIZE [$site getWidth] [$site getHeight] SPACING [$row getSpacing] COUNT [$row getSiteCount]"
 }
 incr nr
}
puts "ROWS $nr"
set nm 0
set first_macro ""
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 set name [$inst getName]
 if {[$master isBlock]} {
  incr nm
  if {[string match {*g_rx*} $name]} {
   puts "RXMACRO $name MASTER [$master getName] SIZE [$master getWidth] [$master getHeight] ORIGIN [$inst getOrigin] ORIENT [$inst getOrient] STATUS [$inst getPlacementStatus]"
   if {$first_macro eq ""} {set first_macro $master}
  }
 }
 if {[string match {*u_rb/wire862394} $name] || [string match {*u_rb/wire805066} $name] || [string match {*u_rb/wire862281} $name]} {
  puts "VIOLATION $name MASTER [$master getName] SIZE [$master getWidth] [$master getHeight] ORIGIN [$inst getOrigin] ORIENT [$inst getOrient] STATUS [$inst getPlacementStatus]"
 }
}
puts "MACROS $nm"
if {$first_macro ne ""} {
 set layers [dict create]
 foreach term [$first_macro getMTerms] {
  foreach pin [$term getMPins] {
   foreach box [$pin getGeometry] {
    set layer [$box getTechLayer]
    if {$layer ne "NULL"} {dict incr layers [$layer getName]}
   }
  }
 }
 puts "RXMACRO_PIN_SHAPES_BY_LAYER $layers"
}
puts "READ_ONLY_PLACEMENT_INSPECTION_COMPLETE"
exit
