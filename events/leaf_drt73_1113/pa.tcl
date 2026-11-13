# LEAF-DRT73-1 proof: DRT pin access on a saved CTS DB, optionally after re-orienting the named hard cores
# env: ODB, OUT (optional write), REORIENT = "inst:orient inst:orient ..." (location = same lower-left box corner)
read_db $::env(ODB)
set block [ord::get_db_block]
foreach pair [split [string trim [expr {[info exists ::env(REORIENT)] ? $::env(REORIENT) : ""}]]] {
  if {$pair eq ""} continue
  # inst:orient[:dx_nm:dy_nm]  (inst names have no ':')
  set f [split $pair ":"]
  set name [lindex $f 0]; set o [lindex $f 1]
  set dx [expr {[llength $f] > 2 ? [lindex $f 2] : 0}]; set dy [expr {[llength $f] > 3 ? [lindex $f 3] : 0}]
  set inst [$block findInst $name]
  set bb [$inst getBBox]; set lx [$bb xMin]; set ly [$bb yMin]; set st [$inst getPlacementStatus]
  $inst setPlacementStatus PLACED
  $inst setOrient $o
  $inst setLocation [expr {$lx + $dx}] [expr {$ly + $dy}]
  $inst setPlacementStatus $st
  set nb [$inst getBBox]
  puts "REORIENT $name -> [$inst getOrient] bbox [$nb xMin] [$nb yMin] [$nb xMax] [$nb yMax] (was $lx $ly, shift $dx $dy nm) status $st"
}
if {[info exists ::env(OUT)]} { write_db $::env(OUT); puts "WROTE $::env(OUT)" }
if {[info exists ::env(SKIP_PA)]} { exit 0 }
set_thread_count 16
set_routing_layers -signal M2-M8
pin_access
puts "PIN_ACCESS_DONE"
