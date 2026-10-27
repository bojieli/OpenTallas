read_db /input/3_place.odb
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set target {u_fcore.rn_bd$_DFF_PN0_}
set found {}
foreach i [$b getInsts] { if {[string map {\\ ""} [$i getName]] eq [string map {\\ ""} $target]} {lappend found $i} }
if {[llength $found] != 1} {error "instance ambiguity $target"}
set i [lindex $found 0]
set x [expr {round(190.08*$dbu)}]; set y [expr {round(185.22*$dbu)}]
set row {}
foreach r [$b getRows] {if {[lindex [$r getOrigin] 1] == $y} {set rb [$r getBBox]; if {[$rb xMin] <= $x && [$rb xMax] > $x} {set row $r; break}}}
if {$row eq ""} {error "no row"}
$i setOrient [$row getOrient]
$i setLocation $x $y
$i setPlacementStatus FIRM
puts "ANCHOR [$i getName] [$i getLocation]"
set target {u_fcore.rn_tx$_DFF_PN0_}
set found {}
foreach i [$b getInsts] { if {[string map {\\ ""} [$i getName]] eq [string map {\\ ""} $target]} {lappend found $i} }
if {[llength $found] != 1} {error "instance ambiguity $target"}
set i [lindex $found 0]
set x [expr {round(189.54*$dbu)}]; set y [expr {round(185.76*$dbu)}]
set row {}
foreach r [$b getRows] {if {[lindex [$r getOrigin] 1] == $y} {set rb [$r getBBox]; if {[$rb xMin] <= $x && [$rb xMax] > $x} {set row $r; break}}}
if {$row eq ""} {error "no row"}
$i setOrient [$row getOrient]
$i setLocation $x $y
$i setPlacementStatus FIRM
puts "ANCHOR [$i getName] [$i getLocation]"
set target {u_fcore.u_rxb.g_block[0].u_block.vp[1]$_DFF_PN0_}
set found {}
foreach i [$b getInsts] { if {[string map {\\ ""} [$i getName]] eq [string map {\\ ""} $target]} {lappend found $i} }
if {[llength $found] != 1} {error "instance ambiguity $target"}
set i [lindex $found 0]
set x [expr {round(190.08*$dbu)}]; set y [expr {round(186.57*$dbu)}]
set row {}
foreach r [$b getRows] {if {[lindex [$r getOrigin] 1] == $y} {set rb [$r getBBox]; if {[$rb xMin] <= $x && [$rb xMax] > $x} {set row $r; break}}}
if {$row eq ""} {error "no row"}
$i setOrient [$row getOrient]
$i setLocation $x $y
$i setPlacementStatus FIRM
puts "ANCHOR [$i getName] [$i getLocation]"
check_placement -verbose
write_db /out/anchored_v3.odb
source /out/geom_dump.tcl
exit
