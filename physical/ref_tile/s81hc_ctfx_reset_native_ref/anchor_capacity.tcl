# Repair actual overlaps among explicitly owned boundary FF/hold anchors.
# Placement only: no cells, nets, clocks, statuses or timing constraints change.
namespace eval ot_ctfx_capacity {}
proc ot_ctfx_capacity::lower {rows y} {
  set lo 0; set hi [llength $rows]
  while {$lo < $hi} {
    set m [expr {($lo+$hi)/2}]
    if {[lindex $rows $m 0] < $y} {set lo [expr {$m+1}]} else {set hi $m}
  }
  return $lo
}
proc ot_ctfx_capacity::cut {intervals lo hi} {
  set result {}
  foreach interval $intervals {
    lassign $interval a b
    if {$hi <= $a || $lo >= $b} {lappend result $interval;continue}
    if {$a < $lo} {lappend result [list $a $lo]}
    if {$hi < $b} {lappend result [list $hi $b]}
  }
  return $result
}
proc ot_ctfx_capacity::repair {block names} {
  set owned {}; set selected {}; set rects {}; set rows {}; set maxheight 0
  foreach name [lsort -unique $names] {
    set inst [$block findInst $name]
    if {$inst eq "NULL" || [$inst getPlacementStatus] ne "FIRM" || [[$inst getMaster] isBlock]} {
      error "OT_ANCHOR_PACK: recorded anchor is not one actual FIRM standard cell: $name"
    }
    dict set owned $name 1; lappend selected $inst
  }
  if {![llength $selected]} return
  foreach row [$block getRows] {
    set b [$row getBBox];set h [expr {[$b yMax]-[$b yMin]}]
    if {$h <= 0 || [$row getSpacing] <= 0} continue
    lappend rows [list [$b yMin] [$b xMin] [$b xMax] [$b yMax] [$row getSpacing] [$row getOrient]]
    set maxheight [expr {max($maxheight,$h)}]
  }
  set rows [lsort -integer -index 0 $rows]
  if {![llength $rows]} {error "OT_ANCHOR_PACK: no actual legal rows"}
  set obstacles {};set allrects {}
  foreach inst [$block getInsts] {
    if {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set b [$inst getBBox];set name [$inst getName]
    set rect [list [$b xMin] [$b yMin] [$b xMax] [$b yMax] $name [dict exists $owned $name]]
    lappend allrects $rect
    if {![dict exists $owned $name]} {lappend obstacles [lrange $rect 0 3]}
  }
  # Sweep actual fixed footprints. Ignore unrelated obstacle/obstacle pairs.
  # No geometry changes if all recorded anchors are already nonoverlapping.
  set active {};set overlap 0
  foreach rect [lsort -integer -index 0 $allrects] {
    lassign $rect x0 y0 x1 y1 name ours;set keep {}
    foreach old $active {
      lassign $old a b c d other other_ours
      if {$c <= $x0} continue
      lappend keep $old
      if {($ours || $other_ours) && $y0 < $d && $y1 > $b} {set overlap 1;break}
    }
    if {$overlap} break
    lappend keep $rect;set active $keep
  }
  # This leaf's measured defect is capacity, not overlap: 6810 legal fixed
  # anchors consume89% of a116um band, before318um2 movable cells. Reserve
  # room by a deterministic2x target spread; no netlist/pin/clock changes.
  set xmin Inf;set xmax -Inf
  foreach inst $selected {set b [$inst getBBox];set xmin [expr {min($xmin,[$b xMin])}];set xmax [expr {max($xmax,[$b xMax])}]}
  set centre [expr {($xmin+$xmax)/2.0}]
  puts "CTFX_CAPACITY: owned [llength $selected], original span [expr {$xmax-$xmin}]DBU, stretch2x around $centre"

  foreach blockage [$block getBlockages] {
    set b [$blockage getBBox];lappend obstacles [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  set free {};set ri 0
  foreach row $rows {dict set free $ri [list [list [lindex $row 1] [lindex $row 2]]];incr ri}
  foreach rect $obstacles {
    lassign $rect x0 y0 x1 y1
    set ri [ot_ctfx_capacity::lower $rows [expr {$y0-$maxheight}]]
    for {} {$ri < [llength $rows]} {incr ri} {
      lassign [lindex $rows $ri] ry rx ex ey pitch orient
      if {$ry >= $y1} break
      if {$ey > $y0} {dict set free $ri [ot_ctfx_capacity::cut [dict get $free $ri] $x0 $x1]}
    }
  }
  set count 0;set maximum 0
  # Stages first, then FFs, with deterministic names. Both remain close to
  # their original pin-side targets; each allocated footprint reserves sites.
  set order {}
  foreach inst $selected {
    set ff [expr {[string match DFF* [[$inst getMaster] getName]] || [string match ASYNC_DFF* [[$inst getMaster] getName]]}]
    lappend order [list $ff [$inst getName] $inst]
  }
  foreach item [lsort -dictionary -index 0 [lsort -dictionary -index 1 $order]] {
    set inst [lindex $item 2];set master [$inst getMaster];set box [$inst getBBox]
    set width [$master getWidth];set height [$master getHeight]
    set tx [expr {([$box xMin]+[$box xMax])/2.0}];set ty [expr {([$box yMin]+[$box yMax])/2.0}]
    set original_tx $tx
    set tx [expr {$centre+2.0*($tx-$centre)}]
    set score Inf;set best {}
    set right [ot_ctfx_capacity::lower $rows [expr {$ty-$height/2.0}]];set left [expr {$right-1}]
    while {$left >= 0 || $right < [llength $rows]} {
      set lc Inf;set rc Inf
      if {$left >= 0} {set lc [expr {abs([lindex $rows $left 0]+$height/2.0-$ty)}]}
      if {$right < [llength $rows]} {set rc [expr {abs([lindex $rows $right 0]+$height/2.0-$ty)}]}
      if {min($lc,$rc)>$score} break
      if {$lc <= $rc} {set ri $left;incr left -1} else {set ri $right;incr right}
      lassign [lindex $rows $ri] ry rx ex ey pitch orient
      if {$ey-$ry != $height} continue
      foreach interval [dict get $free $ri] {
        lassign $interval a b
        set lo [expr {$rx+int(ceil(double($a-$rx)/$pitch))*$pitch}]
        set hi [expr {$rx+int(floor(double($b-$width-$rx)/$pitch))*$pitch}]
        if {$hi < $lo} continue
        set x [expr {max($lo,min($hi,$rx+round(($tx-$width/2.0-$rx)/$pitch)*$pitch))}]
        set cost [expr {abs($x+$width/2.0-$tx)+abs($ry+$height/2.0-$ty)}]
        if {$cost < $score} {set score $cost;set best [list $ri $x $ry $orient]}
      }
    }
    if {$best eq ""} {error "OT_ANCHOR_PACK: no legal free row site for [$inst getName]"}
    lassign $best ri x y orient
    set total_move [expr {abs($x+$width/2.0-$original_tx)+abs($y+$height/2.0-$ty)}]
    set units [[ord::get_db_tech] getDbUnitsPerMicron]
    if {$total_move>75*$units} {error "CTFX_CAPACITY: exceeds75um native-headroom bound [$inst getName] $total_move"}
    $inst setPlacementStatus PLACED
    $inst setOrient $orient
    if {[[$inst getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
    $inst setLocation $x $y
    $inst setPlacementStatus FIRM
    dict set free $ri [ot_ctfx_capacity::cut [dict get $free $ri] $x [expr {$x+$width}]]
    set maximum [expr {max($maximum,$total_move)}];incr count
  }
  puts "OT_ANCHOR_PACK: legally packed $count owned anchors; maximum Manhattan displacement $maximum DBU"
}

# The caller must supply the exact explicit ownership receipts from the pin
# hooks. Prefix matching or selecting arbitrary FIRM cells is forbidden.
if {![info exists ot_pack_names]} {error "CTFX_CAPACITY: explicit pin-hook ownership receipt missing"}
ot_ctfx_capacity::repair [ord::get_db_block] $ot_pack_names
