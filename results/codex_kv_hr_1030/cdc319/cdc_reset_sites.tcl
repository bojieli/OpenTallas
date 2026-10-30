# Placement-only: first reset synchronizer flops land beside their frozen input pins.
# Later reset stages retain GPL sites so their local fanout does not move.
uplevel #0 {
set cb [ord::get_db_block]; set cu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {prefix port} {u_done.u_rrs u_done__rrst_n u_done.u_wrs u_done__wrst_n u_ing.u_rrs u_ing__rrst_n u_ing.u_wrs u_ing__wrst_n} {
  set bt [$cb findBTerm "${port}\[0\]"]
  if {$bt eq "NULL" || $bt eq ""} {error "CDC_RESET missing port $port"}
  set box [lindex [[lindex [$bt getBPins] 0] getBoxes] 0]
  set tx [expr {round(5.4*$cu)}]; set ty [expr {([$box yMin]+[$box yMax])/2}]
  set hit {}
  foreach i [$cb getInsts] {
    if {[string first $prefix [$i getName]] == 0 && [string match "DFF*" [[$i getMaster] getName]] && [regexp {reset_pipe\\?\[0\\?\]} [$i getName]]} {lappend hit $i}
  }
  if {[llength $hit]!=1} {error "CDC_RESET $prefix first FF count [llength $hit]"}
  set i [lindex $hit 0]; set best {}; set mw [[$i getMaster] getWidth]
  foreach r [$cb getRows] {
    lassign [$r getOrigin] ox oy; set sw [[$r getSite] getWidth]
    set x [expr {$ox+round(double($tx-$ox)/$sw)*$sw}]
    set d [expr {abs($x-$tx)+abs($oy-$ty)}]
    if {$best eq "" || $d<[lindex $best 0]} {set best [list $d $x $oy [$r getOrient]]}
  }
  lassign $best d x y o
  $i setPlacementStatus PLACED; $i setOrient $o; $i setLocation $x $y; $i setPlacementStatus FIRM
  puts "CDC_RESET_FIRST [$i getName] [expr {double($x)/$cu}] [expr {double($y)/$cu}]"
}
}
