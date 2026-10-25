# Gap-row repeater legalisation for feedthrough ribbons routed OVER hard cores (cores declaring obs_max below the
# partition top layer, e.g. QC SU lane cores capped at M6 with M7 ribbons). Shared by the G2 skeleton prototype
# (proto_sweep.py) and meant for the partition kit flow (same procs, same order):
#   set ot_gap_bands {{lo hi} ...}; set ot_gap_cores {{x0 y0 x1 y1} ...}; set ot_gap_m <core margin um>
#   ot_gap_before_repair ; repair_design ... ; ot_gap_move_to_rows ; detailed_placement ... ; ot_gap_check_after_dpl 4.0
# Every buffer/inverter that repair_design inserted with its origin inside an over-routable core is moved to the
# nearest legal row of the nearest gap band at the SAME x (the ribbon's x); DPL then resolves overlaps in the band.
# No registers, stages, OBS or layer changes. The check is fail-closed: it prints OT_GAP_FAIL <n> (and the G2
# classifier marks the probe STRUCTURAL) when a moved repeater did not end in a gap band within max_dx of its x.
proc ot_gap_before_repair {} {
  global ot_gap_old
  array unset ot_gap_old
  foreach i [[ord::get_db_block] getInsts] { set ot_gap_old([$i getName]) 1 }
}
proc ot_gap_in_core {x y} {
  global ot_gap_cores
  foreach c $ot_gap_cores {
    lassign $c x0 y0 x1 y1
    if {$x >= $x0 && $x < $x1 && $y >= $y0 && $y < $y1} { return 1 }
  }
  return 0
}
proc ot_gap_move_to_rows {} {
  global ot_gap_old ot_gap_bands ot_gap_m ot_gap_moved
  array unset ot_gap_moved
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
  set row 0.27; set n 0; set fresh 0
  foreach i [$blk getInsts] {
    set nm [$i getName]
    if {[info exists ot_gap_old($nm)]} { continue }
    if {![regexp {^(BUF|INV|HB)} [[$i getMaster] getName]]} { continue }
    incr fresh
    lassign [$i getLocation] lx ly
    set x [expr {$lx/double($dbu)}]; set y [expr {$ly/double($dbu)}]
    if {![ot_gap_in_core $x $y]} { continue }
    set h [expr {[[$i getMaster] getHeight]/double($dbu)}]
    set best ""; set bd 1e30
    foreach b $ot_gap_bands {
      lassign $b lo hi
      set first [expr {$ot_gap_m + ceil(($lo - $ot_gap_m)/$row - 1e-6)*$row}]
      set last  [expr {$ot_gap_m + floor(($hi - $h - $ot_gap_m)/$row + 1e-6)*$row}]
      if {$first > $last + 1e-6} { continue }
      set yy [expr {$ot_gap_m + round(($y - $ot_gap_m)/$row)*$row}]
      if {$yy < $first} { set yy $first }
      if {$yy > $last} { set yy $last }
      if {abs($yy - $y) < $bd} { set bd [expr {abs($yy - $y)}]; set best $yy }
    }
    if {$best eq ""} { error "OT_GAP no gap band row fits $nm" }
    $i setLocation $lx [expr {round($best*$dbu)}]
    $i setPlacementStatus PLACED
    set ot_gap_moved($nm) $x
    incr n
  }
  puts "OT_GAP moved $n of $fresh new repeaters from over-routable cores to gap rows"
}
proc ot_gap_check_after_dpl {{max_dx 4.0}} {
  # PASS = every moved repeater ends OUTSIDE every over-routable core (in the inter-core gap, incl. the clearance
  # rows next to the core edge) and within max_dx of its ribbon x. Ledger: /work/gap_repeaters.tsv
  global ot_gap_moved
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
  set bad {}; set maxdx 0.0; set fh [open /work/gap_repeaters.tsv w]
  puts $fh "inst\tribbon_x\tx\ty\tdx\tin_core\tok"
  foreach nm [lsort [array names ot_gap_moved]] {
    set i [$blk findInst $nm]
    if {$i eq "NULL"} { lappend bad "$nm:missing"; continue }
    set b [$i getBBox]
    set x0 [expr {[$b xMin]/double($dbu)}]; set y0 [expr {[$b yMin]/double($dbu)}]
    set x1 [expr {[$b xMax]/double($dbu)}]; set y1 [expr {[$b yMax]/double($dbu)}]
    set dx [expr {abs($x0 - $ot_gap_moved($nm))}]
    if {$dx > $maxdx} { set maxdx $dx }
    set inc [ot_gap_box_in_core $x0 $y0 $x1 $y1]
    set ok [expr {!$inc && $dx <= $max_dx}]
    puts $fh [format "%s\t%.3f\t%.3f\t%.3f\t%.3f\t%d\t%d" $nm $ot_gap_moved($nm) $x0 $y0 $dx $inc $ok]
    if {!$ok} { lappend bad [format "%s:x=%.3f,y=%.3f,dx=%.3f,in_core=%d" $nm $x0 $y0 $dx $inc] }
  }
  close $fh
  if {[llength $bad]} {
    puts "OT_GAP_FAIL [llength $bad] of [array size ot_gap_moved] moved repeaters inside a core or off the ribbon x: [lrange $bad 0 9]"
  } else {
    puts [format "OT_GAP_PASS %d repeaters in gap rows, max |dx| %.3f um" [array size ot_gap_moved] $maxdx]
  }
}
proc ot_gap_box_in_core {bx0 by0 bx1 by1} {
  global ot_gap_cores
  foreach c $ot_gap_cores {
    lassign $c x0 y0 x1 y1
    if {$bx0 < $x1 - 1e-6 && $bx1 > $x0 + 1e-6 && $by0 < $y1 - 1e-6 && $by1 > $y0 + 1e-6} { return 1 }
  }
  return 0
}
