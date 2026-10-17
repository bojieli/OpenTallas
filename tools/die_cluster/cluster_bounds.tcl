# Cluster bounds check (tools/die_cluster, ROOT CLUSTER-FLOW 2026-10-16) -- run before global_route; fail closed.
# Counts: instances not fully inside the die (GRT-0035 / GRT-0028 source), unplaced instances, ports without a placed
# pin, port pins not inside the die or not touching the outline, nets whose every pin was dropped.  Writes a JSON report
# and returns the number of violations (0 = clean).
proc ot_cluster_bounds {report tag} {
  set block [ord::get_db_block]
  set die [$block getDieArea]
  set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set n_inst 0; set out_inst 0; set unplaced 0; set out_names {}
  foreach inst [$block getInsts] {
    incr n_inst
    set st [$inst getPlacementStatus]
    if {$st eq "NONE" || $st eq "UNPLACED"} { incr unplaced; if {[llength $out_names] < 20} { lappend out_names "unplaced:[$inst getName]" }; continue }
    set bb [$inst getBBox]
    if {[$bb xMin] < $dx0 || [$bb yMin] < $dy0 || [$bb xMax] > $dx1 || [$bb yMax] > $dy1} {
      incr out_inst
      if {[llength $out_names] < 20} { lappend out_names [$inst getName] }
    }
  }
  set n_bt 0; set bt_unplaced 0; set bt_out 0; set bt_off_outline 0; set bt_names {}
  foreach bt [$block getBTerms] {
    incr n_bt
    set bps [$bt getBPins]
    if {[llength $bps] == 0} { incr bt_unplaced; if {[llength $bt_names] < 20} { lappend bt_names "unplaced:[$bt getName]" }; continue }
    foreach bp $bps {
      set st [$bp getPlacementStatus]
      if {$st eq "NONE" || $st eq "UNPLACED"} { incr bt_unplaced; continue }
      foreach box [$bp getBoxes] {
        set x0 [$box xMin]; set y0 [$box yMin]; set x1 [$box xMax]; set y1 [$box yMax]
        if {$x0 < $dx0 || $y0 < $dy0 || $x1 > $dx1 || $y1 > $dy1} {
          incr bt_out; if {[llength $bt_names] < 20} { lappend bt_names "outside:[$bt getName]" }
        } elseif {!($x0 == $dx0 || $y0 == $dy0 || $x1 == $dx1 || $y1 == $dy1)} {
          incr bt_off_outline; if {[llength $bt_names] < 20} { lappend bt_names "off_outline:[$bt getName]" }
        }
      }
    }
  }
  set n_net 0; set single 0
  foreach net [$block getNets] {
    if {[$net isSpecial]} { continue }
    incr n_net
    set k [expr {[llength [$net getITerms]] + [llength [$net getBTerms]]}]
    if {$k == 1} { incr single }
  }
  set viol [expr {$out_inst + $unplaced + $bt_unplaced + $bt_out + $bt_off_outline}]
  set f [open $report w]
  puts $f "{\"schema\": \"opentallas.die_cluster.bounds.v1\", \"tag\": \"$tag\", \"die_dbu\": \[$dx0, $dy0, $dx1, $dy1\],"
  puts $f " \"instances\": $n_inst, \"instances_outside_die\": $out_inst, \"instances_unplaced\": $unplaced,"
  puts $f " \"ports\": $n_bt, \"ports_unplaced\": $bt_unplaced, \"port_pins_outside_die\": $bt_out, \"port_pins_off_outline\": $bt_off_outline,"
  puts $f " \"signal_nets\": $n_net, \"single_terminal_nets\": $single, \"violations\": $viol,"
  set q {}
  foreach s [concat $out_names $bt_names] { lappend q "\"$s\"" }
  puts $f " \"first\": \[[join $q {, }]\]}"
  close $f
  puts "OT_CLUSTER_BOUNDS $tag instances=$n_inst outside=$out_inst unplaced=$unplaced ports=$n_bt ports_unplaced=$bt_unplaced port_pins_outside=$bt_out port_pins_off_outline=$bt_off_outline single_terminal_nets=$single violations=$viol"
  return $viol
}

# Snap legaliser for die-scale clusters (ROOT CLUSTER-FLOW 2026-10-16: OpenROAD detailed_placement allocates its site
# grid for the whole core -- the d4b SW quadrant, 14,970 x 12,820 um = 13 G sites, ran out of 64 GB and 140 GB with only
# 211 buffers to place).  Every movable std cell is clamped into the core, snapped to the site / row grid (row
# orientation), and pushed off any hard macro it lands on (nearest macro edge + one site / row), so no cell or pin is
# outside the die and none sits on a macro.  Std-cell / std-cell overlaps are NOT resolved (GRT does not need it);
# the count of cells moved and of cells still on a macro is reported.  Returns the number still on a macro.
proc ot_cluster_snap_legalize {report} {
  set blk [ord::get_db_block]
  set core [$blk getCoreArea]
  set cx0 [$core xMin]; set cy0 [$core yMin]; set cx1 [$core xMax]; set cy1 [$core yMax]
  set rows [$blk getRows]
  set r0 [lindex $rows 0]
  set site [$r0 getSite]
  set sw [$site getWidth]; set rh [$site getHeight]
  set ry0 [lindex [$r0 getOrigin] 1]
  set rx0 [lindex [$r0 getOrigin] 0]
  set ro0 [$r0 getOrient]
  set ro1 [expr {$ro0 eq "R0" ? "MX" : "R0"}]
  set bin 200000
  array set mb {}
  set macros {}
  foreach inst [$blk getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set bb [$inst getBBox]
    set m [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    set k [llength $macros]; lappend macros $m
    for {set i [expr {[lindex $m 0] / $bin}]} {$i <= [lindex $m 2] / $bin} {incr i} {
      for {set j [expr {[lindex $m 1] / $bin}]} {$j <= [lindex $m 3] / $bin} {incr j} { lappend mb($i,$j) $k }
    }
  }
  set moved 0; set on_macro 0; set n 0
  foreach inst [$blk getInsts] {
    set mst [$inst getMaster]
    if {[$mst isBlock]} { continue }
    set st [$inst getPlacementStatus]
    if {$st eq "FIRM" || $st eq "LOCKED" || $st eq "COVER"} { continue }
    incr n
    set w [$mst getWidth]; set h [$mst getHeight]
    set loc [$inst getLocation]; set x [lindex $loc 0]; set y [lindex $loc 1]
    set x0 $x; set y0 $y
    for {set it 0} {$it < 4} {incr it} {
      if {$x < $cx0} { set x $cx0 }; if {$x + $w > $cx1} { set x [expr {$cx1 - $w}] }
      if {$y < $cy0} { set y $cy0 }; if {$y + $h > $cy1} { set y [expr {$cy1 - $h}] }
      set x [expr {$rx0 + (($x - $rx0) / $sw) * $sw}]
      set y [expr {$ry0 + (($y - $ry0) / $rh) * $rh}]
      if {$x < $cx0} { set x [expr {$x + $sw}] }; if {$y < $cy0} { set y [expr {$y + $rh}] }
      set hit -1
      set ci [expr {($x + $w / 2) / $bin}]; set cj [expr {($y + $h / 2) / $bin}]
      if {[info exists mb($ci,$cj)]} {
        foreach k $mb($ci,$cj) {
          lassign [lindex $macros $k] mx0 my0 mx1 my1
          if {$x < $mx1 && $x + $w > $mx0 && $y < $my1 && $y + $h > $my0} { set hit $k; break }
        }
      }
      if {$hit < 0} { break }
      lassign [lindex $macros $hit] mx0 my0 mx1 my1
      # nearest escape: left / right / below / above the macro, one site / row clear
      set c [list [list [expr {$x - ($mx0 - $sw - $w)}] [expr {$mx0 - $sw - $w}] $y] \
                  [list [expr {($mx1 + $sw) - $x}] [expr {$mx1 + $sw}] $y] \
                  [list [expr {$y - ($my0 - $rh - $h)}] $x [expr {$my0 - $rh - $h}]] \
                  [list [expr {($my1 + $rh) - $y}] $x [expr {$my1 + $rh}]]]
      set best ""
      foreach e [lsort -real -index 0 $c] {
        lassign $e d ex ey
        if {$ex >= $cx0 && $ex + $w <= $cx1 && $ey >= $cy0 && $ey + $h <= $cy1} { set best $e; break }
      }
      if {$best eq ""} { break }
      set x [lindex $best 1]; set y [lindex $best 2]
    }
    if {$hit >= 0} { incr on_macro }
    set orient [expr {((($y - $ry0) / $rh) % 2) == 0 ? $ro0 : $ro1}]
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
    if {$x != $x0 || $y != $y0} { incr moved }
  }
  set f [open $report w]
  puts $f "{\"schema\": \"opentallas.die_cluster.snap_legalize.v1\", \"std_cells\": $n, \"moved\": $moved, \"still_on_macro\": $on_macro, \"stdcell_overlaps\": \"not resolved\"}"
  close $f
  puts "OT_CLUSTER_SNAP_LEGAL std_cells=$n moved=$moved still_on_macro=$on_macro"
  return $on_macro
}
