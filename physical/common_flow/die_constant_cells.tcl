# Materialize structural Verilog straps as real ASAP7 tie cells before PA.
# one_/zero_ implicit POWER/GROUND nets are not signal wiring. Never relabel
# those nets or suppress router power errors. This is pre-PDN mapping only:
# mapped cells still require real M1 supply rails/upconnect in the die PDN.
# Only constant cells are placed. Cache occupied intervals for rows actually
# used; never allocate a full standard-cell placement grid across the die.
proc ot_const_place {block ties} {
  set rows {}
  foreach row [$block getRows] {
    set bb [$row getBBox]
    lappend rows [list [$bb yMin] [$bb xMin] [$bb xMax] [$bb yMax] [$row getSpacing] [$row getOrient]]
  }
  set rows [lsort -integer -index 0 $rows]
  if {![llength $rows]} { error "OT_CONST: no physical standard-cell rows" }
  set obstacles {}
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] in {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} continue
    if {[$inst getPlacementStatus] eq "NONE" || [$inst getPlacementStatus] eq "UNPLACED"} {
      error "OT_CONST: non-constant instance [$inst getName] is not placed"
    }
    set bb [$inst getBBox]
    lappend obstacles [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
  }
  set blocked {}; set occupied {}
  foreach inst $ties {
    lassign [$inst getLocation] tx ty
    set width [[$inst getMaster] getWidth]; set height [[$inst getMaster] getHeight]
    set start [lsearch -bisect -integer -index 0 $rows $ty]
    if {$start < 0} { set start 0 }
    set found 0
    for {set delta 0} {$delta < [llength $rows] && !$found} {incr delta} {
      set indices [expr {$delta ? [list [expr {$start-$delta}] [expr {$start+$delta}]] : [list $start]}]
      foreach ri $indices {
        if {$ri < 0 || $ri >= [llength $rows]} continue
        lassign [lindex $rows $ri] ry rx ex ey pitch orient
        if {$pitch <= 0 || $height > $ey-$ry} continue
        if {![dict exists $blocked $ri]} {
          set spans {}
          foreach box $obstacles {
            lassign $box x0 y0 x1 y1
            if {$y0 < $ry+$height && $y1 > $ry} { lappend spans [list $x0 $x1] }
          }
          dict set blocked $ri $spans
        }
        set spans [dict get $blocked $ri]
        if {[dict exists $occupied $ri]} { set spans [concat $spans [dict get $occupied $ri]] }
        # Include a sentinel at the row end to evaluate the final free gap.
        lappend spans [list $ex $ex]
        set cursor $rx; set best {}; set best_distance Inf
        foreach span [lsort -integer -index 0 $spans] {
          lassign $span left right
          set lo [expr {$rx + int(ceil(double($cursor-$rx)/$pitch))*$pitch}]
          set hi [expr {$rx + int(floor(double(min($left,$ex)-$width-$rx)/$pitch))*$pitch}]
          if {$lo <= $hi} {
            set x [expr {$rx + round(double($tx-$rx)/$pitch)*$pitch}]
            set x [expr {max($lo,min($x,$hi))}]
            set distance [expr {abs($x-$tx)}]
            if {$distance < $best_distance} { set best $x; set best_distance $distance }
          }
          set cursor [expr {max($cursor,$right)}]
          if {$cursor >= $ex} break
        }
        if {$best eq ""} continue
        $inst setOrient $orient
        $inst setLocation $best $ry
        $inst setPlacementStatus FIRM
        dict lappend occupied $ri [list $best [expr {$best+$width}]]
        set found 1
        break
      }
    }
    if {!$found} { error "OT_CONST: no legal row gap for [$inst getName]" }
  }
  puts "OT_CONST LOCAL_PLACE cells=[llength $ties] rows_used=[dict size $occupied]"
}
proc ot_die_constant_cells {} {
  set platform /OpenROAD-flow-scripts/flow/platforms/asap7
  if {![llength [get_lib_pins -quiet TIEHIx1_ASAP7_75t_R/H]] ||
      ![llength [get_lib_pins -quiet TIELOx1_ASAP7_75t_R/L]]} {
    foreach lib [glob $platform/lib/NLDM/*SIMPLE*RVT_TT*.lib*] { read_liberty $lib }
  }
  set block [ord::get_db_block]
  set macros {}
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] isBlock]} {
      dict set macros [$inst getName] [list [$inst getLocation] [$inst getOrient]]
    }
  }
  foreach pin {TIEHIx1_ASAP7_75t_R/H TIELOx1_ASAP7_75t_R/L} {
    if {[llength [get_lib_pins -quiet */$pin]] != 1} { error "OT_CONST: missing actual ASAP7 tie pin $pin" }
    insert_tiecells $pin
    repair_tie_fanout -separation 1 -max_fanout 1 $pin
  }
  add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
  add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
  global_connect
  set count 0; set ties {}
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] in {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} { incr count; lappend ties $inst }
  }
  if {$count} { ot_const_place $block $ties }
  dict for {name original} $macros {
    set inst [$block findInst $name]
    if {[list [$inst getLocation] [$inst getOrient]] ne $original} {
      error "OT_CONST: constant legalization moved hard macro $name"
    }
  }
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] ni {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} continue
    foreach pin {VDD VSS} {
      set it [$inst findITerm $pin]
      if {$it eq "NULL" || [$it getNet] eq "NULL" || ![[$it getNet] isSpecial]} {
        error "OT_CONST: missing logical supply binding [$inst getName]/$pin"
      }
    }
  }
  foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND} && ![$net isSpecial]} {
      error "OT_CONST: unmapped power/ground signal net [$net getName]"
    }
  }
  puts "OT_CONST MAPPED cells=$count hard_macros_unchanged=[dict size $macros]"
  if {$count} {
    puts "OT_CONST PG_OPEN: actual M1 supply rails and upconnect require PDN connectivity qualification"
  }
}
ot_die_constant_cells
