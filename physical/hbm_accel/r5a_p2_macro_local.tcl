# P2's 96 SRAMs form 32 three-macro quarter banks inside eight SM-local tiles.
# This is a new source-owned bank arrangement, not an e11 geometry replay.
source /src/physical/common/ot_macro_track_snap.tcl
set block [ord::get_db_block]
set dbu [ot_mts::get_dbu]
set core [$block getCoreArea]
set cx [expr {double([$core xMin])/$dbu}]
set cy [expr {double([$core yMin])/$dbu}]
set keyed {}
foreach inst [$block getInsts] {
  if {![[$inst getMaster] isBlock]} {continue}
  set name [$inst getName]
  if {![regexp {sm\[([0-7])\]\.bank\[([0-3])\]\.(.*)} $name -> m q tail]} {
    error "P2 unexpected macro instance: $name"
  }
  if {[regexp {half\[([01])\]\.u_ram} $tail -> h]} {set slot $h} elseif {$tail eq "ecc_ram"} {set slot 2} else {error "P2 unexpected bank macro: $name"}
  lappend keyed [list $m $q $slot $inst]
  $inst setPlacementStatus NONE
}
if {[llength $keyed]!=96} {error "P2 requires all 96 payload and protection SRAMs"}
set seen [dict create]
foreach item $keyed {
  lassign $item m q slot inst
  set key "$m,$q,$slot"
  if {[dict exists $seen $key]} {error "P2 duplicate bank slot $key"}
  dict set seen $key 1
  set x [expr {$cx+36.288+($m%4)*475.2+($q%2)*220.32}]
  set y [expr {$cy+36.288+($m/4)*950.4+($q/2)*400.032+$slot*46.08}]
  ot_mts::place $inst $x $y R0 LOCKED
  set box [$inst getBBox]
  if {[$box xMax]>[$core xMax] || [$box yMax]>[$core yMax]} {error "P2 macro $key outside allocated core"}
}
puts "OT_R5A_P2_MACRO_LOCAL banks=32 macros=96 tile_columns=4 tile_rows=2"
ot_mts::assert_on_track -label r5a_p2_macro_local
