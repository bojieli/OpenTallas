# Zero-cycle station: keep the original second reset landing in the free middle band.
set cr_b [ord::get_db_block]
set cr_u [$cr_b getDbUnitsPerMicron]
set cr_hits {}
foreach cr_i [$cr_b getInsts] {
 if {[string match {u_p.g_pin.rst_l1*} [$cr_i getName]] && [string match {DFF*} [[$cr_i getMaster] getName]]} { lappend cr_hits $cr_i }
}
if {[llength $cr_hits] != 1} { error "CAPC4_RESET_EXPECTED_ONE [llength $cr_hits]" }
set cr_i [lindex $cr_hits 0]
set cr_x [expr {round(172.0*$cr_u)}]
set cr_target [expr {190.0*$cr_u}]
set cr_best {}; set cr_dist 1e30
foreach cr_row [$cr_b getRows] {
 set cr_z [$cr_row getBBox]
 if {$cr_x < [$cr_z xMin] || $cr_x+2*$cr_u > [$cr_z xMax]} { continue }
 set cr_y [$cr_z yMin]
 set cr_d [expr {abs($cr_y-$cr_target)}]
 if {$cr_d < $cr_dist} { set cr_dist $cr_d; set cr_best $cr_row }
}
if {$cr_best eq {}} {error "CAPC4_NO_RESET_ROW"}
set cr_z [$cr_best getBBox]
set cr_pitch [$cr_best getSpacing]
set cr_x [expr {[$cr_z xMin]+round(double($cr_x-[$cr_z xMin])/$cr_pitch)*$cr_pitch}]
set cr_y [$cr_z yMin]
$cr_i setOrient [$cr_best getOrient]
$cr_i setLocation $cr_x $cr_y
$cr_i setPlacementStatus FIRM
set cr_bb [$cr_i getBBox]
foreach cr_m [$cr_b getInsts] {
 if {![[$cr_m getMaster] isBlock]} {continue}
 set cr_mb [$cr_m getBBox]
 if {[$cr_bb xMin] < [$cr_mb xMax] && [$cr_bb xMax] > [$cr_mb xMin] && [$cr_bb yMin] < [$cr_mb yMax] && [$cr_bb yMax] > [$cr_mb yMin]} {error "CAPC4_RESET_OVERLAP [$cr_m getName]"}
}
puts "CAPC4_RESET_STATION [$cr_i getName] [expr {double($cr_x)/$cr_u}] [expr {double($cr_y)/$cr_u}] unchanged2edge"
