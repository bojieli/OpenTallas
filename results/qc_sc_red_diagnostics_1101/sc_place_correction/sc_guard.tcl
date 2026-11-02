# Exact clock/FF endpoint and whole source-graph guard for one private comb-only placement.
set ::scb [ord::get_db_block]
proc sc_cells {} {set d {};foreach i [$::scb getInsts] {dict set d [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]};return $d}
proc sc_inc {} {set d {};foreach i [$::scb getInsts] {foreach t [$i getITerms] {set n [$t getNet];dict set d [list [$i getName] [[$t getMTerm] getName]] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]}};return $d}
proc sc_nets {} {set d {};foreach n [$::scb getNets] {dict set d [$n getName] [list [$n getSigType] [$n isSpecial] [$n isDoNotTouch]]};return $d}
proc sc_terms {} {set d {};foreach t [$::scb getBTerms] {set n [$t getNet];set boxes {};foreach p [$t getBPins] {foreach bb [$p getBoxes] {lappend boxes [list [[$bb getTechLayer] getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]}};dict set d [$t getName] [list [$t getIoType] [$t getSigType] [expr {$n eq "NULL" ? "NULL" : [$n getName]}] $boxes]};return $d}
proc sc_endpoint {name st} {expr {[string match DFF* [lindex $st 0]] || [string match sc_ck_* $name]}}
proc sc_restore_and_lock {} {
 dict for {name st} $::sc_expected_cells {
  set i [$::scb findInst $name];if {$i eq "NULL"} {error "SC_PLACE_MISSING $name"}
  set flag [$i isDoNotTouch];if {$flag} {$i setDoNotTouch 0}
  if {[sc_endpoint $name $st]} {
   if {[$i getOrient] ne [lindex $st 2] || [$i getLocation] ne [lindex $st 1]} {
    # OpenDB rejects pose setters on FIRM even when the requested orientation matches.
    # Release only a face hook's changed endpoint, restore the exact reviewed pose, and lock again.
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {$i setPlacementStatus PLACED}
    $i setOrient [lindex $st 2];$i setLocation {*}[lindex $st 1]
   }
   $i setPlacementStatus FIRM
  }
  $i setDoNotTouch [lindex $st 4]
 }
 dict for {name st} $::sc_expected_nets {set n [$::scb findNet $name];if {$n eq "NULL"} {error "SC_PLACE_NET_MISSING $name"};$n setDoNotTouch [lindex $st 2]}
}
proc sc_check {tag mode} {
 set now [sc_cells];if {[dict size $now]!=[dict size $::sc_expected_cells]} {error "SC_PLACE_CELL_COUNT $tag"}
 dict for {name st} $::sc_expected_cells {
  if {![dict exists $now $name]} {error "SC_PLACE_CELL_MISSING $tag $name"};set cur [dict get $now $name]
  if {[lindex $cur 0] ne [lindex $st 0] || [lindex $cur 4] ne [lindex $st 4]} {error "SC_PLACE_MASTER_FLAGS_CHANGED $tag $name"}
  if {[sc_endpoint $name $st]} {
   set want $st;if {$mode eq "firm"} {lset want 3 FIRM}
   if {$cur ne $want} {error "SC_PLACE_ENDPOINT_CHANGED $tag $name $cur != $want"}
  }
 }
 if {[sc_inc] ne $::sc_expected_inc} {error "SC_PLACE_SOURCE_GRAPH_CHANGED $tag"}
 if {[sc_terms] ne $::sc_expected_terms || [sc_nets] ne $::sc_expected_nets} {error "SC_PLACE_PIN_NET_CHANGED $tag"}
 puts "SC_PLACE_GUARD_PASS $tag all_FF_clock_poses_masters_sourcepins_graph"
}
