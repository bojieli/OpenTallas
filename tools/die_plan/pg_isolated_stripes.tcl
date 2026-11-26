# Only exact, isolated PG stripe fragments may enter the stock reserve splitter.
proc kcg_bounds {box} {
  return [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
}

proc kcg_touches {first second} {
  lassign $first ax ay bx by
  lassign $second cx cy dx dy
  return [expr {$ax <= $dx && $cx <= $bx && $ay <= $dy && $cy <= $by}]
}

proc kcg_level {layer} {
  if {$layer ne "NULL" && $layer ne "" && [regexp {^M([0-9]+)$} [$layer getName] -> level]} { return $level }
  return 0
}

proc kcg_via_levels {box} {
  if {![$box isVia]} {
    set level [kcg_level [$box getTechLayer]]
    return [list $level $level]
  }
  foreach via [list [$box getBlockVia] [$box getTechVia]] {
    if {$via ne "NULL" && $via ne ""} {
      return [list [kcg_level [$via getBottomLayer]] [kcg_level [$via getTopLayer]]]
    }
  }
  return {}
}

proc kcg_may_remove_via {levels cut_layer stripe_layers} {
  if {![llength $levels]} { return 1 }
  lassign $levels bottom top
  if {$bottom <= $cut_layer && $cut_layer <= $top} { return 1 }
  # The stock splitter can also remove a lower via if no surviving strap
  # layer between its top and the cut anchors that stack.
  if {$bottom < 2 || $top >= $cut_layer} { return 0 }
  foreach layer $stripe_layers {
    if {$top <= $layer && $layer < $cut_layer} { return 0 }
  }
  return 1
}

proc kcg_exact_windows {expected} {
  set block [ord::get_db_block]
  set dbu [$block getDbUnitsPerMicron]
  set targets {}
  foreach row $expected {
    lassign $row net level rect
    set dbrect [lmap value $rect {expr {round($value*$dbu)}}]
    lappend targets [list $net $level $rect $dbrect]
  }
  set exact {}
  set nearby {}
  set stripe_layers {}
  set pg_nets {}
  foreach name {VDD VSS} {
    set net [$block findNet $name]
    if {$net eq "NULL" || $net eq ""} { continue }
    lappend pg_nets $net
    foreach swire [$net getSWires] {
      foreach box [$swire getWires] {
        set kind [$box getWireShapeType]
        set is_via [expr {[$box isVia] || $kind eq "DRCFILL"}]
        set layer 0
        if {!$is_via} {
          set layer [kcg_level [$box getTechLayer]]
          if {$kind ne "FOLLOWPIN" && $layer ni $stripe_layers} { lappend stripe_layers $layer }
        }
        set bounds [kcg_bounds $box]
        foreach target $targets {
          lassign $target net_name cut_layer rect dbrect
          if {(!$is_via && $layer != $cut_layer) || ![kcg_touches $bounds $dbrect]} { continue }
          if {!$is_via && $kind eq "STRIPE" && $name eq $net_name && $bounds eq $dbrect} {
            dict incr exact $target
          } elseif {$is_via} {
            dict lappend nearby $target [list "PG via or fill" [kcg_via_levels $box]]
          } else {
            dict lappend nearby $target [list "same-layer PG metal" {}]
          }
        }
      }
    }
  }
  set active {}
  foreach target $targets {
    lassign $target net_name cut_layer rect dbrect
    if {![dict exists $exact $target]} {
      puts "OT_PG_ISOLATED_STRIPE already absent $net_name M$cut_layer $rect"
      continue
    }
    if {[dict get $exact $target] != 1} {
      error "OT_PG_ISOLATED_STRIPE duplicate exact fragment $net_name M$cut_layer $rect"
    }
    if {[dict exists $nearby $target]} {
      foreach contact [dict get $nearby $target] {
        lassign $contact kind levels
        if {$kind eq "same-layer PG metal" || [kcg_may_remove_via $levels $cut_layer $stripe_layers]} {
          error "OT_PG_ISOLATED_STRIPE $kind touches $net_name M$cut_layer $rect"
        }
      }
    }
    lappend active $target
  }
  if {![llength $active]} { return {} }
  foreach net $pg_nets {
    foreach term [$net getBTerms] {
      foreach pin [$term getBPins] {
        foreach box [$pin getBoxes] {
          set layer [kcg_level [$box getTechLayer]]
          foreach target $active {
            lassign $target name cut_layer rect dbrect
            if {$layer == $cut_layer && [kcg_touches [kcg_bounds $box] $dbrect]} {
              error "OT_PG_ISOLATED_STRIPE power port [$term getName] touches $name M$cut_layer $rect"
            }
          }
        }
      }
    }
  }
  foreach inst [$block getInsts] {
    if {[$inst getPlacementStatus] in {NONE UNPLACED}} { continue }
    set bounds [kcg_bounds [$inst getBBox]]
    foreach target $active {
      lassign $target name cut_layer rect dbrect
      if {[kcg_touches $bounds $dbrect]} {
        error "OT_PG_ISOLATED_STRIPE placed instance [$inst getName] touches $name M$cut_layer $rect"
      }
    }
  }
  return [lmap target $active {
    lassign $target name cut_layer rect
    puts "OT_PG_ISOLATED_STRIPE exact $name M$cut_layer $rect"
    concat $rect [list [list $cut_layer]]
  }]
}
