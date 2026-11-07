# DH81-HOST 11-07 (opt-in OT_HOST_XGRID, sourced from face_flops.tcl after relay_mid): place the opt-in lane1 crossing
# stages and the hub codecs FIRM before GPL, released with the relay list before DPL.  GPL has no reason to spread free
# flops along a long straight wire: vA and vB put lane1's whole adapter in the empty gap with 650-700 um hops.
#   u_xg rx stage 1, tx stage, rx stage 2: vertical strips on the line from the N-pin hub to the E grid, bit-ordered.
#   u_ctl_tx, u_ctl_rx: rectangles below their own N pin windows, so the h_rx/h_tx wires stay short.
# Rectangles (um): OT_HOST_XGRID_RECTS = {regex x0 y0 x1 y1} ...
uplevel #0 {
set hx_blk [ord::get_db_block]
set hx_rows [$hx_blk getRows]
set hx_sw [[[lindex $hx_rows 0] getSite] getWidth]
set hx_rh [[[lindex $hx_rows 0] getSite] getHeight]
set hx_core [$hx_blk getCoreArea]
set hx_x0 [$hx_core xMin]; set hx_y0 [$hx_core yMin]
set hx_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set hx_orient {}
foreach r $hx_rows { dict set hx_orient [lindex [$r getOrigin] 1] [$r getOrient] }
proc hx_bit {n} {
  set n [string map {\\ {}} $n]
  if {[regexp {\[(\d+)\]\$_} $n -> b]} { return [expr {int($b)}] }
  return -1
}
set hx_out [open $::env(RESULTS_DIR)/ot_relay_mid.txt a]
set hx_taken {}
foreach {hx_re hx_a hx_b hx_c hx_d} $::env(OT_HOST_XGRID_RECTS) {
  set l {}
  foreach i [$hx_blk getInsts] {
    set m [$i getMaster]
    if {[$m isBlock] || ![string match "*DFF*" [$m getName]]} continue
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
    set nm [string map {\\ {}} [$i getName]]
    if {![regexp $hx_re $nm]} continue
    lappend l [list [hx_bit [$i getName]] $nm $i]
  }
  set l [lsort -integer -index 0 [lsort -index 1 $l]]
  set n [llength $l]
  if {$n == 0} { puts "OT_HOST_XGRID WARN no flops match $hx_re"; continue }
  set X0 [expr {int($hx_a * $hx_dbu)}]; set Y0 [expr {int($hx_b * $hx_dbu)}]
  set W [expr {int(($hx_c - $hx_a) * $hx_dbu)}]; set H [expr {int(($hx_d - $hx_b) * $hx_dbu)}]
  set rows [expr {max(1, int($H / (2 * $hx_rh)))}]
  set cols [expr {max(1, int(ceil(double($n) / $rows)))}]
  set px [expr {$W / $cols}]
  if {$px < 24 * $hx_sw} { puts "OT_HOST_XGRID WARN $hx_re: $n flops tight in rect, column pitch [expr {double($px) / $hx_dbu}] um" }
  set k 0
  foreach e $l {
    set c [lindex $e 2]
    set cx [expr {$X0 + ($k / $rows) * $px}]
    set cy [expr {$Y0 + ($k % $rows) * 2 * $hx_rh}]
    set cx [expr {$hx_x0 + (($cx - $hx_x0) / $hx_sw) * $hx_sw}]
    set cy [expr {$hx_y0 + (($cy - $hx_y0) / $hx_rh) * $hx_rh}]
    $c setLocation $cx $cy
    if {[dict exists $hx_orient $cy]} { $c setOrient [dict get $hx_orient $cy] }
    $c setPlacementStatus FIRM
    puts $hx_out [$c getName]
    incr k
  }
  puts "OT_HOST_XGRID placed $n flops FIRM for '$hx_re' in ($hx_a $hx_b $hx_c $hx_d), $cols cols $rows rows"
}
close $hx_out
}
