# P5 eight-slot XO ring aperture. The generator supplies a single typed,
# explicitly enabled band and the earlier landing hook's protected cell list.
namespace eval ::ot_p5_xo_spread {}

proc ::ot_p5_xo_spread::box {b} {
  return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}

proc ::ot_p5_xo_spread::remove {spans lo hi} {
  set left {}
  foreach span $spans {
    lassign $span a b
    if {$b <= $lo || $a >= $hi} {
      lappend left $span
    } else {
      if {$a < $lo} { lappend left [list $a $lo] }
      if {$b > $hi} { lappend left [list $hi $b] }
    }
  }
  return $left
}

proc ::ot_p5_xo_spread::block {rows_name rr box rect} {
  upvar 1 $rows_name rows
  lassign $box a b c d
  lassign $rect x0 y0 x1 y1
  if {$c <= $x0 || $a >= $x1 || $d <= $y0 || $b >= $y1} { return }
  set y [expr {$y0+int(floor(double($b-$y0)/$rr))*$rr}]
  for {} {$y < $d} {incr y $rr} {
    if {![dict exists $rows $y]} continue
    lassign [dict get $rows $y] orient origin sw spans
    dict set rows $y [list $orient $origin $sw [remove $spans $a $c]]
  }
}

proc ::ot_p5_xo_spread::slot {rows_name instmeta rect scale limit rr} {
  upvar 1 $rows_name rows
  lassign $instmeta inst x y w orient
  lassign $rect x0 y0 x1 y1
  set tx [expr {max($x0,min($x1-$w,int(round($x1+($x-$x1)*$scale))))}]
  set best {}
  set cost [expr {$limit+1}]
  foreach delta {0 -2 2 -4 4 -6 6} {
    set yy [expr {$y+$delta*$rr}]
    if {![dict exists $rows $yy]} continue
    lassign [dict get $rows $yy] row_orient row_x sw spans
    # Keep the existing vertical rail polarity. An X-axis row mirror can
    # coexist with the instance's legal left/right mirror.
    if {($row_orient in {MX R180}) != ($orient in {MX R180})} continue
    foreach span $spans {
      lassign $span a b
      set lo [expr {$row_x+int(ceil(double($a-$row_x)/$sw))*$sw}]
      set hi [expr {$row_x+int(floor(double($b-$w-$row_x)/$sw))*$sw}]
      if {$lo > $hi} continue
      set xx [expr {$row_x+int(round(double($tx-$row_x)/$sw))*$sw}]
      set xx [expr {max($lo,min($hi,$xx))}]
      set d [expr {abs($xx-$tx)+abs($yy-$y)}]
      if {$d < $cost} { set best [list $xx $yy]; set cost $d }
    }
  }
  if {![llength $best]} {
    error "OT_P5_XO_SPREAD [$inst getName]: no same-orientation cell site within $limit DBU of ($tx,$y)"
  }
  lassign $best nx ny
  block rows $rr [list $nx $ny [expr {$nx+$w}] [expr {$ny+$rr}]] $rect
  return [list $inst $nx $ny]
}

proc ::ot_p5_xo_spread::run {block prefix rect_um scale halo_um limit_um protected mode {projected_boxes {}}} {
  if {$mode ni {price apply} || ![llength $protected]} { error "OT_P5_XO_SPREAD expected protected footprint" }
  set u [$block getDbUnitsPerMicron]
  set rect [lmap x $rect_um {expr {int(round($x*$u))}}]
  lassign $rect x0 y0 x1 y1
  set halo [expr {int(round($halo_um*$u))}]
  set limit [expr {int(round($limit_um*$u))}]
  set rows {}
  set rr -1
  foreach row [$block getRows] {
    set site [$row getSite]
    set sw [$row getSpacing]
    lassign [$row getOrigin] rx ry
    set h [$site getHeight]
    set right [expr {$rx+[$row getSiteCount]*$sw}]
    set a [expr {max($rx,$x0)}]
    set b [expr {min($right,$x1)}]
    if {$a >= $b || $ry<$y0 || $ry+$h>$y1} continue
    if {$sw <= 0 || ($rr > 0 && $rr != $h)} { error "OT_P5_XO_SPREAD foreign row geometry" }
    set rr $h
    set orient [$row getOrient]
    if {[dict exists $rows $ry]} {
      lassign [dict get $rows $ry] ro rx0 rw spans
      if {$ro ne $orient || $rw!=$sw || (($rx-$rx0)%$sw)!=0} { error "OT_P5_XO_SPREAD inconsistent row fragments" }
      lappend spans [list $a $b]
    } else {
      set rx0 $rx
      set spans [list [list $a $b]]
    }
    dict set rows $ry [list $orient $rx0 $sw $spans]
  }
  if {$rr <= 0} { error "OT_P5_XO_SPREAD no writable standard-cell rows" }
  set y0 [lindex [lsort -integer [dict keys $rows]] 0]
  set rect [list $x0 $y0 $x1 $y1]
  foreach anchor_y [dict keys $rows] {
    if {($anchor_y-$y0)%$rr != 0} {error "OT_P5_XO_SPREAD inconsistent vertical row lattice"}
  }

  set keep {}
  foreach name $protected {
    if {[$block findInst $name] eq "NULL"} { error "OT_P5_XO_SPREAD missing scoped landing anchor $name" }
    dict set keep $name 1
  }
  foreach blockage [$block getBlockages] { block rows $rr [box [$blockage getBBox]] $rect }
  if {[llength $projected_boxes] && $mode ne "price"} { error "OT_P5_XO_SPREAD projected boxes require price mode" }
  foreach b $projected_boxes { block rows $rr [lmap x $b {expr {int(round($x*$u))}}] $rect }

  set work {}
  set storage 0
  set read 0
  foreach inst [$block getInsts] {
    set bbox [$inst getBBox]
    lassign [box $bbox] a b c d
    set master [$inst getMaster]
    if {[$master isBlock]} {
      block rows $rr [list [expr {$a-$halo}] [expr {$b-$halo}] [expr {$c+$halo}] [expr {$d+$halo}]] $rect
      continue
    }
    if {$c <= $x0 || $a >= $x1 || $d <= $y0 || $b >= $y1} continue
    set name [$inst getName]
    set status [$inst getPlacementStatus]
    set match [expr {[string first "$prefix/" $name]==0 && ![dict exists $keep $name]}]
    set inserted_wire [expr {[regexp {/wire[0-9]+$} $name] && [regexp {^(BUF|INV|BUFx|INVx)} [$master getName]]}]
    if {!$match || $inserted_wire || $b<$y0 || $d>$y1 || $d-$b!=$rr || ($a+$c)/2<$x0 || ($a+$c)/2>$x1
        || $status in {LOCKED COVER FROZEN} || ![dict exists $rows $b]} {
      block rows $rr [list $a $b $c $d] $rect
      continue
    }
    if {[regexp {\.sd_c\\?\[\d+\\?\]\$} $name]} { incr storage }
    if {[regexp {\.u_dsel/y\\?\[\d+\\?\]\$} $name]} { incr read }
    lappend work [list $a $inst $a $b [expr {$c-$a}] [$inst getOrient]]
  }
  if {$storage < 8000 || $read < 995 || [llength $work] < 10000} {
    error "OT_P5_XO_SPREAD underfilled eight-slot landing: $storage storage, $read read, [llength $work] total"
  }
  set moves {}
  foreach item [lsort -integer -index 3 [lsort -integer -decreasing -index 0 $work]] {
    lappend moves [slot rows [lrange $item 1 end] $rect $scale $limit $rr]
  }
  if {$mode eq "apply"} {
    foreach move $moves {
      lassign $move inst x y
      set status [$inst getPlacementStatus]
      if {$status eq "FIRM"} { $inst setPlacementStatus PLACED }
      $inst setLocation $x $y
      if {$status eq "FIRM"} { $inst setPlacementStatus FIRM }
    }
  }
  puts "OT_P5_XO_SPREAD $mode: [llength $moves] cells, $storage storage and $read read, unchanged logical phase"
  return $moves
}

# Scope locked by gen_phys to the qualified four-slot XO band. Compute every
# same-row seat before changing the block. The epoch reader has its own seat.
namespace eval ::ot_p5_xo_d4 {}

proc ::ot_p5_xo_d4::box {b} {
  return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}

proc ::ot_p5_xo_d4::reserve {rowsvar y0 rh rect} {
  upvar 1 $rowsvar rows
  lassign $rect a b c d
  set y [expr {$y0 + int(floor(double($b-$y0)/$rh))*$rh}]
  for {} {$y < $d} {incr y $rh} {
    if {![dict exists $rows $y]} continue
    lassign [dict get $rows $y] orient rx sw spans
    set free {}
    foreach span $spans {
      lassign $span lo hi
      if {$c <= $lo || $a >= $hi} {
        lappend free $span
      } else {
        if {$lo < $a} {lappend free [list $lo $a]}
        if {$c < $hi} {lappend free [list $c $hi]}
      }
    }
    dict set rows $y [list $orient $rx $sw $free]
  }
}

proc ::ot_p5_xo_d4::pick {spans rx sw left right target width} {
  set result {}
  set best 1000000000
  foreach rect $spans {
    lassign $rect a c
    set lo [expr {$rx+int(ceil(double(max($a,$left)-$rx)/$sw))*$sw}]
    set hi [expr {$rx+int(floor(double(min($c,$right)-$width-$rx)/$sw))*$sw}]
    if {$lo > $hi} continue
    set x [expr {$rx+int(round(double($target-$rx)/$sw))*$sw}]
    set x [expr {max($lo,min($hi,$x))}]
    set q [expr {abs($x-$target)}]
    if {$q < $best || ($q == $best && $x < $result)} {
      set result $x
      set best $q
    }
  }
  return $result
}

proc ::ot_p5_xo_d4::run {block rect_um x_cut_um delta_um epoch_um mode} {
  if {$mode ni {price apply}} {error "OT_P5_XO_D4 invalid mode"}
  set u [$block getDbUnitsPerMicron]
  lassign [lmap v $rect_um {expr {round($v*$u)}}] x0 y_min x1 y1
  lassign [lmap v $epoch_um {expr {round($v*$u)}}] ex ey
  set floor [expr {round($x_cut_um*$u)}]
  set dx [expr {round($delta_um*$u)}]
  set limit [expr {round(16.2*$u)}]
  set prefix "u_bound.u_cland_xo_i0/"
  set rows {}
  set rh 0
  foreach row [$block getRows] {
    lassign [box [$row getBBox]] a b c d
    if {$c <= $x0 || $a >= $x1 || $b < $y_min || $d > $y1} continue
    set w [$row getSpacing]
    set h [expr {$d-$b}]
    if {$w<=0 || $h<=0 || ($rh && $rh!=$h)} {error "OT_P5_XO_D4 unexpected row lattice"}
    set rh $h
    set face [$row getOrient]
    set spans {}
    set rx $a
    if {[dict exists $rows $b]} {
      lassign [dict get $rows $b] old_face rx old_w spans
      if {$old_face ne $face || $old_w != $w || ($a-$rx)%$w} {error "OT_P5_XO_D4 inconsistent row fragments"}
    }
    lappend spans [list [expr {max($a,$x0)}] [expr {min($c,$x1)}]]
    dict set rows $b [list $face $rx $w $spans]
  }
  if {!$rh || ![dict exists $rows $ey]} {error "OT_P5_XO_D4 no legal epoch row"}
  set y0 [lindex [lsort -integer [dict keys $rows]] 0]
  foreach y [dict keys $rows] {if {($y-$y0)%$rh} {error "OT_P5_XO_D4 inconsistent row spacing"}}
  foreach blockaged [$block getBlockages] {reserve rows $y0 $rh [box [$blockaged getBBox]]}

  set storage 0
  set reads 0
  set epoch {}
  set work {}
  foreach inst [$block getInsts] {
    set name [$inst getName]
    set local [expr {[string first $prefix $name] == 0}]
    set is_storage [expr {$local && [regexp {\.sd_c\\?\[\d+\\?\]\$} $name]}]
    set is_reader [expr {$local && [regexp {\.u_dsel/y\\?\[\d+\\?\]\$} $name]}]
    incr storage $is_storage
    incr reads $is_reader
    lassign [box [$inst getBBox]] a b c d
    if {$c <= $x0 || $a >= $x1 || $d <= $y_min || $b >= $y1} continue
    set status [$inst getPlacementStatus]
    set master [$inst getMaster]
    set movable [expr {$local && ![$master isBlock] && $status ni {LOCKED COVER FROZEN}
                       && $b >= $y_min && $d <= $y1 && $d-$b == $rh && [dict exists $rows $b]}]
    if {$is_reader && [regexp {\.dch\\?\[17\\?\]\.u_dsel/y\\?\[16\\?\]\$_DFF_P_$} $name]} {
      if {!$movable || [llength $epoch]} {error "OT_P5_XO_D4 missing or duplicate unheld epoch reader"}
      set epoch [list $inst [expr {$c-$a}] $status]
      continue
    }
    if {!$movable || ($a+$c)/2 < $floor} {
      reserve rows $y0 $rh [list $a $b $c $d]
      continue
    }
    lassign [dict get $rows $b] row_orient rx sw _spans
    if {($a-$rx)%$sw || ($c-$a)%$sw || ($row_orient in {MX R180}) != ([$inst getOrient] in {MX R180})} {
      error "OT_P5_XO_D4 unexpected placed member lattice $name"
    }
    # This local ring group owns data nets only. A clock buffer inserted in
    # the hierarchy must remain with the clock owner.
    if {!$is_storage && !$is_reader && [regexp {^(BUF|INV|CLK)} [$master getName]]} {
      set is_clock_driver 0
      foreach it [$inst getITerms] {
        if {[$it isOutputSignal] && [$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK"} {set is_clock_driver 1}
      }
      if {$is_clock_driver} {reserve rows $y0 $rh [list $a $b $c $d]; continue}
    }
    dict lappend work $b [list $a $inst [expr {$c-$a}] $status]
  }

  set pins 0
  foreach pin [$block getBTerms] {
    if {[$pin getIoType] eq "INPUT" && [regexp {^xo_i0\[\d+\]$} [$pin getName]]} {incr pins}
  }
  if {$pins != 1105 || $storage != 4420 || $reads != 1105 || ![llength $epoch] || ![dict size $work]} {
    error "OT_P5_XO_D4 mismatched four-slot source: $pins pins, $storage storage, $reads readers"
  }
  lassign $epoch ei ew estatus
  lassign [dict get $rows $ey] eorient eorigin esw espans
  if {[pick $espans $eorigin $esw $ex [expr {$ex+$ew}] $ex $ew] ne $ex} {
    error "OT_P5_XO_D4 epoch reader has no exact legal reserved seat"
  }
  reserve rows $y0 $rh [list $ex $ey [expr {$ex+$ew}] [expr {$ey+$rh}]]
  set moves [list [list $ei $ex $ey $estatus $eorient]]

  dict for {y group} $work {
    set right $x1
    foreach entry [lsort -integer -decreasing -index 0 $group] {
      lassign $entry a inst width status
      lassign [dict get $rows $y] rorient rx sw spans
      set target [expr {min($a+$dx,$right-$width)}]
      set x [pick $spans $rx $sw [expr {max($x0,$a-$limit)}] $right $target $width]
      if {$x eq "" || abs($x-$a)>$limit} {error "OT_P5_XO_D4 no bounded same-row seat for [$inst getName]"}
      lappend moves [list $inst $x $y $status [$inst getOrient]]
      set right $x
    }
  }
  if {$mode eq "apply"} {
    foreach row $moves {
      lassign $row inst x y orig_status orientation
      if {$orig_status eq "FIRM"} {$inst setPlacementStatus PLACED}
      $inst setOrient $orientation
      $inst setLocation $x $y
      if {$orig_status eq "FIRM"} {$inst setPlacementStatus FIRM}
    }
  }
  puts "OT_P5_XO_D4 $mode: [llength $moves] exact-row positions, 4420 storage, 1105 readers, unchanged clock/reset edges"
  return $moves
}

proc ::ot_p5_xo_d4::run_select_profile {block mode} {
  if {$mode ni {price apply}} {error "OT_P5_XO_D4 invalid mode"}
  set u [$block getDbUnitsPerMicron]
  if {$u != 1000} {error "OT_P5_XO_D4 select profile requires the qualified 1000-DBU lattice"}
  set rect_um {1356.48 972 1438.56 1226.88}
  set x_cut_um 1400
  set delta_um 17.28
  set epoch_um {1397.412 1024.38}
  lassign [lmap v $rect_um {expr {round($v*$u)}}] x0 y_min x1 y1
  lassign [lmap v $epoch_um {expr {round($v*$u)}}] ex ey
  set floor [expr {round($x_cut_um*$u)}]
  set dx [expr {round($delta_um*$u)}]
  set limit [expr {round(20.52*$u)}]
  set prefix "u_bound.u_cland_xo_i0/"
  set rows {}
  set rh 0
  foreach row [$block getRows] {
    lassign [box [$row getBBox]] a b c d
    if {$c <= $x0 || $a >= $x1 || $b < $y_min || $d > $y1} continue
    set w [$row getSpacing]
    set h [expr {$d-$b}]
    if {$w<=0 || $h<=0 || ($rh && $rh!=$h)} {error "OT_P5_XO_D4 unexpected row lattice"}
    set rh $h
    set face [$row getOrient]
    set spans {}
    set rx $a
    if {[dict exists $rows $b]} {
      lassign [dict get $rows $b] old_face rx old_w spans
      if {$old_face ne $face || $old_w != $w || ($a-$rx)%$w} {error "OT_P5_XO_D4 inconsistent row fragments"}
    }
    lappend spans [list [expr {max($a,$x0)}] [expr {min($c,$x1)}]]
    dict set rows $b [list $face $rx $w $spans]
  }
  if {!$rh || ![dict exists $rows $ey]} {error "OT_P5_XO_D4 no legal epoch row"}
  set y0 [lindex [lsort -integer [dict keys $rows]] 0]
  foreach y [dict keys $rows] {if {($y-$y0)%$rh} {error "OT_P5_XO_D4 inconsistent row spacing"}}
  foreach blockaged [$block getBlockages] {reserve rows $y0 $rh [box [$blockaged getBBox]]}

  set unoccupied_rows $rows
  set storage 0
  set reads 0
  set epoch {}
  set work {}
  set selectors 0
  set read_rows {}
  set read_work {}
  set epoch_obstacle {}
  foreach inst [$block getInsts] {
    set name [$inst getName]
    set local [expr {[string first $prefix $name] == 0}]
    set is_storage [expr {$local && [regexp {\.sd_c\\?\[\d+\\?\]\$} $name]}]
    set is_reader [expr {$local && [regexp {\.u_dsel/y\\?\[\d+\\?\]\$} $name]}]
    incr storage $is_storage
    incr reads $is_reader
    set is_dsel [expr {$local && [regexp {\.dch\\?\[(\d+)\\?\]\.u_dsel/} $name whole ch]}]
    set is_selector [expr {$is_dsel && [regexp {\.u_sel\.di\\?\[\d+\\?\]\$_DFFE_PP_$} $name]}]
    incr selectors $is_selector
    if {$is_reader && $is_dsel} {dict lappend read_rows $ch [[$inst getBBox] yMin]}
    lassign [box [$inst getBBox]] a b c d
    if {$c <= $x0 || $a >= $x1 || $d <= $y_min || $b >= $y1} continue
    set status [$inst getPlacementStatus]
    set master [$inst getMaster]
    set movable [expr {$local && ![$master isBlock] && $status ni {LOCKED COVER FROZEN}
                       && $b >= $y_min && $d <= $y1 && $d-$b == $rh && [dict exists $rows $b]}]
    if {$is_reader && [regexp {\.dch\\?\[17\\?\]\.u_dsel/y\\?\[16\\?\]\$_DFF_P_$} $name]} {
      if {!$movable || [llength $epoch]} {error "OT_P5_XO_D4 missing or duplicate unheld epoch reader"}
      set epoch [list $inst [expr {$c-$a}] $status]
      continue
    }
    if {!$movable} {
      reserve rows $y0 $rh [list $a $b $c $d]
      continue
    }
    lassign [dict get $rows $b] row_orient rx sw _spans
    if {($a-$rx)%$sw || ($c-$a)%$sw || ($row_orient in {MX R180}) != ([$inst getOrient] in {MX R180})} {
      error "OT_P5_XO_D4 unexpected placed member lattice $name"
    }
    # This local ring group owns data nets only. A clock buffer inserted in
    # the hierarchy must remain with the clock owner.
    if {!$is_storage && !$is_reader && [regexp {^(BUF|INV|CLK)} [$master getName]]} {
      set is_clock_driver 0
      foreach it [$inst getITerms] {
        if {[$it isOutputSignal] && [$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK"} {set is_clock_driver 1}
      }
      if {$is_clock_driver} {reserve rows $y0 $rh [list $a $b $c $d]; continue}
    }
    if {$b == $ey && $a < $ex+1188 && $c > $ex} {
      if {!$is_dsel || ![regexp {^INVx1_} [$master getName]] || [llength $epoch_obstacle]} {
        error "OT_P5_XO_D4 unqualified epoch obstacle $name"
      }
      set epoch_obstacle [list $a $b $inst [expr {$c-$a}] $status]
      continue
    }
    if {$is_dsel && !$is_reader} {
      if {$is_selector || ![regexp {\$_DFF} $name]} {
        lappend read_work [list $is_selector $ch $a $b $inst [expr {$c-$a}] $status]
      }
      reserve rows $y0 $rh [list $a $b $c $d]
      continue
    }
    if {$is_dsel || ($a+$c)/2 < $floor} {
      reserve rows $y0 $rh [list $a $b $c $d]
      continue
    }
    dict lappend work $b [list $a $inst [expr {$c-$a}] $status]
  }

  set pins 0
  foreach pin [$block getBTerms] {
    if {[$pin getIoType] eq "INPUT" && [regexp {^xo_i0\[\d+\]$} [$pin getName]]} {incr pins}
  }
  if {$pins != 1105 || $storage != 4420 || $reads != 1105 || ![llength $epoch] || ![dict size $work]} {
    error "OT_P5_XO_D4 mismatched four-slot source: $pins pins, $storage storage, $reads readers"
  }
  if {$selectors != 556 || [dict size $read_rows] != 18} {
    error "OT_P5_XO_D4 mismatched read selector replicas ($selectors, [dict size $read_rows] channels)"
  }
  lassign $epoch ei ew estatus
  if {$ew != 1188} {error "OT_P5_XO_D4 unexpected epoch master width"}
  lassign [dict get $rows $ey] eorient eorigin esw espans
  if {[pick $espans $eorigin $esw $ex [expr {$ex+$ew}] $ex $ew] ne $ex} {
    error "OT_P5_XO_D4 epoch reader has no exact legal reserved seat"
  }
  reserve rows $y0 $rh [list $ex $ey [expr {$ex+$ew}] [expr {$ey+$rh}]]
  set moves [list [list $ei $ex $ey $estatus $eorient]]

  dict for {y group} $work {
    set right $x1
    foreach entry [lsort -integer -decreasing -index 0 $group] {
      lassign $entry a inst width status
      lassign [dict get $rows $y] rorient rx sw spans
      set target [expr {min($a+$dx,$right-$width)}]
      set x [pick $spans $rx $sw [expr {max($x0,$a-$limit)}] $right $target $width]
      if {$x eq "" || abs($x-$a)>$limit} {error "OT_P5_XO_D4 no bounded same-row seat for [$inst getName]"}
      lappend moves [list $inst $x $y $status [$inst getOrient]]
      reserve rows $y0 $rh [list $x $y [expr {$x+$width}] [expr {$y+$rh}]]
      set right $x
    }
  }
  if {[llength $epoch_obstacle]} {
    lassign $epoch_obstacle a y inst width status
    lassign [dict get $rows $y] orient rx sw spans
    set x [pick $spans $rx $sw [expr {max($x0,$a-40*$sw)}] [expr {min($x1,$a+40*$sw+$width)}] $a $width]
    if {$x eq ""} {error "OT_P5_XO_D4 no local epoch-obstacle seat"}
    reserve rows $y0 $rh [list $x $y [expr {$x+$width}] [expr {$y+$rh}]]
    lappend moves [list $inst $x $y $status [$inst getOrient]]
  }
  set centers {}
  dict for {ch coords} $read_rows {
    set ys [lsort -integer $coords]
    set m [expr {[llength $ys]/2}]
    set q [lindex $ys $m]
    if {[llength $ys]%2 == 0} {set q [expr {($q+[lindex $ys [expr {$m-1}]])/2}]}
    dict set centers $ch $q
  }
  set candidates {}
  set movable_old {}
  foreach member $read_work {
    lassign $member selector ch a b inst width status
    set c [dict get $centers $ch]
    set ytarget [expr {max($c-23000,min($c+23000,$b))}]
    set xtarget $a
    if {!$selector} {
      set ytarget [expr {$b+round(0.65*($ytarget-$b))}]
      set xtarget [expr {1410000+round(1.35*($a-1410000))}]
    }
    if {abs($ytarget-$b)>2000 || abs($xtarget-$a)>2000} {
      lappend candidates [list [expr {!$selector}] $ytarget $xtarget $a $b $inst $width $status]
      dict set movable_old $inst 1
    }
  }
  # Rebuild availability after choosing the second phase. The first phase
  # preserved the original read occupancy, so its committed seats are fixed
  # obstacles when the select cells move to their same-orientation rows.
  set rows $unoccupied_rows
  foreach move $moves {dict set movable_old [lindex $move 0] 1}
  foreach inst [$block getInsts] {
    if {[dict exists $movable_old $inst]} continue
    lassign [box [$inst getBBox]] a b c d
    if {$c>$x0 && $a<$x1 && $d>$y_min && $b<$y1} {reserve rows $y0 $rh [list $a $b $c $d]}
  }
  foreach move $moves {
    lassign $move inst x y
    lassign [box [$inst getBBox]] a b c d
    reserve rows $y0 $rh [list $x $y [expr {$x+$c-$a}] [expr {$y+$rh}]]
  }
  set candidates [lsort -integer -index 0 [lsort -integer -index 1 $candidates]]
  foreach member $candidates {
    lassign $member logic yt xt a b inst width status
    set candidates_by_distance {}
    set center [expr {$y0+int(floor(double($yt-$y0)/$rh))*$rh}]
    for {set ry [expr {$center-38*$rh}]} {$ry<=$center+38*$rh} {incr ry $rh} {
      if {($ry-$b)%(2*$rh) || ![dict exists $rows $ry]} continue
      lappend candidates_by_distance [list [expr {abs($ry-$yt)}] $ry]
    }
    set best {}
    foreach pair [lsort -integer -index 0 $candidates_by_distance] {
      lassign $pair dy ry
      if {[llength $best] && $dy>[lindex $best 0]} break
      lassign [dict get $rows $ry] orient rx sw spans
      if {($orient in {MX R180}) != ([$inst getOrient] in {MX R180})} continue
      set x [pick $spans $rx $sw [expr {max($x0,$a-320*$sw)}] [expr {min($x1,$a+$width+320*$sw)}] $xt $width]
      if {$x eq ""} continue
      set cost [expr {$dy+abs($x-$xt)}]
      if {![llength $best] || $cost<[lindex $best 0]} {set best [list $cost $ry $x]}
    }
    if {![llength $best]} {error "OT_P5_XO_D4 no select seat for [$inst getName]"}
    lassign $best cost ry x
    reserve rows $y0 $rh [list $x $ry [expr {$x+$width}] [expr {$ry+$rh}]]
    lappend moves [list $inst $x $ry $status [$inst getOrient]]
  }
  if {$mode eq "apply"} {
    foreach row $moves {
      lassign $row inst x y orig_status orientation
      if {$orig_status eq "FIRM"} {$inst setPlacementStatus PLACED}
      $inst setOrient $orientation
      $inst setLocation $x $y
      if {$orig_status eq "FIRM"} {$inst setPlacementStatus FIRM}
    }
  }
  puts "OT_P5_XO_D4_SELECT $mode: [llength $moves] exact-row positions, 4420 storage, 1105 readers, unchanged clock/reset edges"
  return $moves
}
