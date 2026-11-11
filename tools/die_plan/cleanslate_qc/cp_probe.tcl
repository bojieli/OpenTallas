# CORE-PLACE-1 GRT-only probe (DO_NOT_COUNT): kit odb -> hard cores placed per a plan placement (moves.txt:
# "<sanitized-inst-suffix> <x> <y> <orient>", x/y = plan origin + track offset = place_macro -location) -> every
# std cell unfixed and re-placed (global_placement from the current positions + detailed_placement, same density for
# both arms) -> global_route M2-M7, N congestion iterations, -allow_congestion.  No CTS, no DRT.
# env: ODB, MOVES, DENSITY, ITERS, OUT, ADJ ("M2 0.5 M3 0.5 ..." layer adjustments)
read_db $::env(ODB)
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
proc san {s} { regsub -all {[^A-Za-z0-9]+} $s _ s; return [string trim $s _] }
array set mv {}
set fh [open $::env(MOVES)]
while {[gets $fh line] >= 0} {
  if {[string trim $line] eq "" || [string index $line 0] eq "#"} continue
  lassign $line key x y o
  set mv($key) [list $x $y $o]
}
close $fh
set nmac 0; set nmoved 0; set miss {}
set mkeys [array names mv]
foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  incr nmac
  set nm [san [$i getName]]
  set hit ""
  foreach k $mkeys { if {[string match "*_$k" $nm] || $nm eq $k} { if {$hit eq "" || [string length $k] > [string length $hit]} { set hit $k } } }
  if {$hit eq ""} { lappend miss [$i getName]; continue }
  lassign $mv($hit) x y o
  set ob [$i getBBox]
  set d [expr {max(abs([$ob xMin]/double($dbu) - $x), abs([$ob yMin]/double($dbu) - $y))}]
  if {$d > 0.01 || [$i getOrient] ne $o} { puts "CP_PROBE move $hit from [expr {[$ob xMin]/double($dbu)}],[expr {[$ob yMin]/double($dbu)}] [$i getOrient] to $x,$y $o" }
  $i setPlacementStatus PLACED
  $i setOrient $o
  # setLocation is the origin of the orient-transformed master; place_macro -location = lower-left of the bbox
  $i setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]
  set bb [$i getBBox]
  set dx [expr {round($x*$dbu) - [$bb xMin]}]; set dy [expr {round($y*$dbu) - [$bb yMin]}]
  $i setLocation [expr {[lindex [$i getLocation] 0] + $dx}] [expr {[lindex [$i getLocation] 1] + $dy}]
  $i setPlacementStatus FIRM
  incr nmoved
}
puts "CP_PROBE macros $nmac placed_from_moves $nmoved missing [llength $miss] [lrange $miss 0 5]"
if {[llength $miss]} { error "CP_PROBE: macros without a move line" }
# std cells: physical-only fixed cells (taps/endcaps/fill) under a macro are removed, every other cell unfixed
set rm 0; set unf 0
set mbb {}
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { lappend mbb [$i getBBox] } }
foreach i [$b getInsts] {
  set m [$i getMaster]
  if {[$m isBlock]} continue
  set sig 0
  foreach it [$i getITerms] { if {[$it getSigType] ni {POWER GROUND}} { if {[$it getNet] ne "NULL"} { set sig 1; break } } }
  if {!$sig} {
    set ib [$i getBBox]; set over 0
    foreach bb $mbb { if {[$ib xMin] < [$bb xMax] && [$ib xMax] > [$bb xMin] && [$ib yMin] < [$bb yMax] && [$ib yMax] > [$bb yMin]} { set over 1; break } }
    if {$over} { odb::dbInst_destroy $i; incr rm }
    continue
  }
  if {[$i getPlacementStatus] ne "PLACED"} { $i setPlacementStatus PLACED; incr unf }
}
puts "CP_PROBE removed_phys_under_macro $rm unfixed $unf"
if {[info exists ::env(SMOKE)]} { puts "CP_PROBE_SMOKE_OK"; exit 0 }
set t0 [clock seconds]
global_placement -skip_initial_place -density $::env(DENSITY) -pad_left 0 -pad_right 0
detailed_placement
puts "CP_PROBE_PLACE_DONE [expr {[clock seconds]-$t0}] s"
write_db $::env(OUT)/placed.odb
set_routing_layers -signal M2-M7 -clock M2-M7
foreach {l a} $::env(ADJ) { set_global_routing_layer_adjustment $l $a }
set t1 [clock seconds]
global_route -congestion_iterations $::env(ITERS) -allow_congestion -verbose -congestion_report_file $::env(OUT)/grt.congestion.rpt
puts "CP_PROBE_GRT_DONE [expr {[clock seconds]-$t1}] s"
