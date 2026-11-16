# KV-Q2-CLK-1115: clock tap-buffer centroid rule (POST_CTS, kit hook).
# TritonCTS puts each H-tree branch buffer at its sub-region centre. With macros the centre lies on a macro blockage and the
# buffer lands in the nearest free gap, up to 115 um from the leaf buffers it drives (q2: clkbuf_5_23_0 at the macro gap,
# its 5 leaves on the E strip). The star net then carries 70+ ps of routed RC that the CTS estimate does not see and the
# related-pair skew reaches 121-132 ps. Rule: every branch buffer (clkbuf_<lvl>_*, lvl >= 1, not leaf, not root) whose
# load centre is > OT_TAP_UM from the driver moves to that centre (bottom-up, level descending), unless the centre is inside a
# macro (+halo); its dummy clkload cells follow it. Placement is re-legalised after. No cell is added, no connection changes.
# Env: OT_TAP_UM (default 30), OT_TAP_REPORT_ONLY=1.
proc ctc_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set ctc_um [ctc_env OT_TAP_UM 30.0]
set ctc_ro [ctc_env OT_TAP_REPORT_ONLY 0]
set ctc_blk [ord::get_db_block]
set ctc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ctc_mac {}
foreach i [$ctc_blk getInsts] { if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend ctc_mac [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] } }
set ctc_halo [expr {int(4 * $ctc_dbu)}]
set ctc_list {}
foreach i [$ctc_blk getInsts] {
  if {[regexp {^clkbuf_([0-9]+)_[0-9]+_[0-9]+_} [$i getName] -> lvl] && $lvl >= 1} { lappend ctc_list [list $lvl $i] }
}
set ctc_moved 0; set ctc_skip_mac 0; set ctc_seen 0
foreach e [lsort -integer -decreasing -index 0 $ctc_list] {
  set inst [lindex $e 1]
  set out ""
  foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set out $it } }
  if {$out eq "" || [$out getNet] eq "NULL"} continue
  set xs {}; set ys {}; set dum {}
  foreach it [[$out getNet] getITerms] {
    if {![$it isInputSignal]} continue
    set li [$it getInst]
    if {[string match clkload* [$li getName]]} { lappend dum $li; continue }
    set b [$li getBBox]
    lappend xs [expr {([$b xMin] + [$b xMax]) / 2}]; lappend ys [expr {([$b yMin] + [$b yMax]) / 2}]
  }
  if {[llength $xs] == 0} continue
  incr ctc_seen
  set cx [expr {([tcl::mathfunc::max {*}$xs] + [tcl::mathfunc::min {*}$xs]) / 2}]
  set cy [expr {([tcl::mathfunc::max {*}$ys] + [tcl::mathfunc::min {*}$ys]) / 2}]
  set db [$inst getBBox]
  set dx [expr {([$db xMin] + [$db xMax]) / 2}]; set dy [expr {([$db yMin] + [$db yMax]) / 2}]
  set dist [expr {(abs($cx - $dx) + abs($cy - $dy)) / double($ctc_dbu)}]
  if {$dist <= $ctc_um} continue
  set inmac 0
  foreach m $ctc_mac {
    lassign $m x0 y0 x1 y1
    if {$cx > $x0 - $ctc_halo && $cx < $x1 + $ctc_halo && $cy > $y0 - $ctc_halo && $cy < $y1 + $ctc_halo} { set inmac 1; break }
  }
  if {$inmac} { incr ctc_skip_mac; puts [format "OT_TAP skip_macro %s dist %.1f" [$inst getName] $dist]; continue }
  puts [format "OT_TAP move %s lvl %d dist %.1f -> (%.1f,%.1f)" [$inst getName] [lindex $e 0] $dist [expr {$cx/double($ctc_dbu)}] [expr {$cy/double($ctc_dbu)}]]
  if {$ctc_ro} continue
  set hw [expr {([$db xMax] - [$db xMin]) / 2}]; set hh [expr {([$db yMax] - [$db yMin]) / 2}]
  $inst setLocation [expr {int($cx - $hw)}] [expr {int($cy - $hh)}]
  $inst setPlacementStatus PLACED
  foreach d $dum { $d setLocation [expr {int($cx - $hw)}] [expr {int($cy - $hh)}]; $d setPlacementStatus PLACED }
  incr ctc_moved
}
puts "OT_TAP summary branch_buffers $ctc_seen moved $ctc_moved skip_macro $ctc_skip_mac radius_um $ctc_um report_only $ctc_ro"
if {$ctc_moved > 0} {
  if {[catch {detailed_placement} ctc_msg]} { error "OT_TAP: detailed placement after tap move failed: $ctc_msg" }
  check_placement -verbose
}
