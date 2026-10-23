# PRE_GLOBAL_PLACE hook (STW-S81e-XR 10-23, u_xr xrt3u register floorplan): place planned register groups FIRM inside
# their planned boxes through global placement (released to PLACED before DPL by reg_floorplan_release.tcl).
# Why: a stage that only copies a register (zero-logic hop pin flop -> copy) has the same HPWL anywhere on the line between
# its source and its consumer, so wirelength-driven GPL leaves the split of a long two-hop path to chance (GPL collapses
# relay chains, 10-22).  Anchoring the copies fixes the split: the long hop is the zero-logic wire and the logic hop is
# short.  Placement only; 0 cycles, no netlist change.
# Input: $::env(OT_REG_PLACE) lines "<tcl regexp on the instance name, backslashes stripped> <x0> <y0> <x1> <y1>" (um).
# Only sequential cells (DFF* / SDF* / ASYNC*) are anchored.  An entry that matches no flop is an error (renamed by
# synthesis -> the plan no longer applies).  Placed names -> $RESULTS_DIR/ot_reg_floorplan.txt.
set ot_rf_blk [ord::get_db_block]
set ot_rf_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_rf_rows [$ot_rf_blk getRows]
set ot_rf_site [[lindex $ot_rf_rows 0] getSite]
set ot_rf_sw [$ot_rf_site getWidth]
set ot_rf_rh [$ot_rf_site getHeight]
set ot_rf_orient {}
set ot_rf_y0s {}
foreach r $ot_rf_rows { set y [lindex [$r getOrigin] 1]; dict set ot_rf_orient $y [$r getOrient]; lappend ot_rf_y0s $y }
set ot_rf_x0 [lindex [[lindex $ot_rf_rows 0] getOrigin] 0]
set ot_rf_plan {}
set fh [open $::env(OT_REG_PLACE) r]
foreach ln [split [read $fh] "\n"] {
  set ln [string trim $ln]
  if {$ln eq "" || [string index $ln 0] eq "#"} continue
  lappend ot_rf_plan $ln
}
close $fh
set ot_rf_all {}
foreach i [$ot_rf_blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  if {![regexp {^(DFF|SDF|ASYNC)} [[$i getMaster] getName]]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
  lappend ot_rf_all [list [string map {\\ {}} [$i getName]] $i]
}
set ot_rf_all [lsort -dictionary -index 0 $ot_rf_all]
set ot_rf_out [open $::env(RESULTS_DIR)/ot_reg_floorplan.txt w]
set ot_rf_done {}
set ot_rf_tot 0
foreach ln $ot_rf_plan {
  # plain whitespace split (a Tcl list read would eat the regexp's backslashes)
  if {![regexp {^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$} $ln -> re bx0 by0 bx1 by1]} { error "OT_REG_PLACE: bad line '$ln'" }
  set cells {}
  foreach p $ot_rf_all {
    set n [lindex $p 0]
    if {[dict exists $ot_rf_done $n]} continue
    if {[regexp -- $re $n]} { lappend cells [lindex $p 1]; dict set ot_rf_done $n 1 }
  }
  if {[llength $cells] == 0} { error "OT_REG_PLACE: '$re' matches no flop" }
  set X0 [expr {round($bx0 * $ot_rf_dbu)}]; set X1 [expr {round($bx1 * $ot_rf_dbu)}]
  set Y0 [expr {round($by0 * $ot_rf_dbu)}]; set Y1 [expr {round($by1 * $ot_rf_dbu)}]
  # rows inside the box, then fill column-major (bit order runs along y) with one site of gap between cells
  set rys {}
  foreach y [lsort -integer -unique $ot_rf_y0s] { if {$y >= $Y0 && $y + $ot_rf_rh <= $Y1} { lappend rys $y } }
  if {[llength $rys] == 0} { error "OT_REG_PLACE: box $bx0 $by0 $bx1 $by1 holds no row" }
  set x [expr {$ot_rf_x0 + (($X0 - $ot_rf_x0 + $ot_rf_sw - 1) / $ot_rf_sw) * $ot_rf_sw}]
  set ri 0; set colw 0; set n 0
  foreach i $cells {
    set w [[$i getMaster] getWidth]
    if {$ri >= [llength $rys]} {
      set x [expr {$x + $colw + $ot_rf_sw}]; set ri 0; set colw 0
    }
    if {$x + $w > $X1} { error "OT_REG_PLACE: box for '$re' too small ([llength $cells] flops)" }
    set y [lindex $rys $ri]
    $i setOrient [dict get $ot_rf_orient $y]
    $i setLocation $x $y
    $i setPlacementStatus FIRM
    puts $ot_rf_out [$i getName]
    if {$w > $colw} { set colw $w }
    incr ri; incr n
  }
  puts "OT_REG_PLACE '$re': $n flops FIRM in $bx0 $by0 $bx1 $by1"
  incr ot_rf_tot $n
}
close $ot_rf_out
puts "OT_REG_PLACE total $ot_rf_tot flops"
