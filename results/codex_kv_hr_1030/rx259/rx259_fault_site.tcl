# Placement-only minimax site for an internal fault register with all-face captures.
uplevel #0 {
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {stem xpos} {u_rx.base_fault$ 129.6 u_rx.queue_fault$ 132.3} {
set hits {}
foreach i [$b getInsts] {if {[string first $stem [$i getName]]==0 && [string match DFF* [[$i getMaster] getName]]} {lappend hits $i}}
if {[llength $hits]!=1} {error "RX259 internal fault first FF count [llength $hits]"}
set i [lindex $hits 0];set tx [expr {$xpos*$u}];set ty [expr {129.6*$u}];set best {}
foreach r [$b getRows] {lassign [$r getOrigin] ox oy;set sw [[$r getSite] getWidth];set x [expr {$ox+round(double($tx-$ox)/$sw)*$sw}];set d [expr {abs($x-$tx)+abs($oy-$ty)}];if {$best eq "" || $d<[lindex $best 0]} {set best [list $d $x $oy [$r getOrient]]}}
lassign $best d x y o;$i setPlacementStatus PLACED;$i setOrient $o;$i setLocation $x $y;$i setPlacementStatus FIRM
puts "RX259_FAULT_SITE [$i getName] [expr {double($x)/$u}] [expr {double($y)/$u}]"
}
}
