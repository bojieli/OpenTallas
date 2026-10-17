# Temporary M6 PORT-only routing guard. The router must index M6 to access
# VIA56; all M6 outside actual E/W terminal rectangles stays obstructed.
# Explicit add/remove is idempotent, including on an ECO's final routed DB.
proc ot_m6_pin_access_apply {} {
if {![info exists ::ot_m6_pin_access_mode] || $::ot_m6_pin_access_mode ni {add remove}} {
  error "OT_M6_PIN_ACCESS requires explicit mode add/remove"
}
if {![info exists ::ot_m6_stub_um] || ![string is double -strict $::ot_m6_stub_um] || $::ot_m6_stub_um <= 0 || $::ot_m6_stub_um > 1} {
  error "OT_M6_PIN_ACCESS invalid stub depth"
}
set m6pa_blk [ord::get_db_block]
set m6pa_tech [ord::get_db_tech]
set m6pa_u [$m6pa_blk getDbUnitsPerMicron]
set m6pa_die [$m6pa_blk getDieArea]
set m6pa_l [$m6pa_tech findLayer M6]
set m6pa_s [expr {round($::ot_m6_stub_um * $m6pa_u)}]
set m6pa_n 0
set m6pa_spans [dict create W {} E {}]
foreach bt [$m6pa_blk getBTerms] {
  if {[$bt getSigType] in {POWER GROUND}} continue
  foreach bp [$bt getBPins] {
    foreach bx [$bp getBoxes] {
      if {[[$bx getTechLayer] getName] ne "M6"} continue
      set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
      if {$x0 == [$m6pa_die xMin]} {
        set face W; set nx0 $x0; set nx1 [expr {$x0 + $m6pa_s}]
      } elseif {$x1 == [$m6pa_die xMax]} {
        set face E; set nx1 $x1; set nx0 [expr {$x1 - $m6pa_s}]
      } else { error "OT_M6_PIN_ACCESS M6 pin [$bt getName] is not on the W/E face" }
      if {$x1 - $x0 < $m6pa_s} {
        if {$::ot_m6_pin_access_mode eq "remove"} { error "OT_M6_PIN_ACCESS remove before pin deepening" }
        odb::dbBox_destroy $bx
        odb::dbBox_create $bp $m6pa_l $nx0 $y0 $nx1 $y1
        incr m6pa_n
      }
      dict lappend m6pa_spans $face [list $y0 $y1]
    }
  }
}
set m6pa_rects [list [list [expr {[$m6pa_die xMin] + $m6pa_s}] [$m6pa_die yMin] [expr {[$m6pa_die xMax] - $m6pa_s}] [$m6pa_die yMax]]]
# Fill the gaps in each face band. Leaving the entire band open permitted
# six M6 doglegs outside their terminal's y span in the actual w130-w2 DEF.
foreach face {W E} {
  if {$face eq "W"} {
    set a [$m6pa_die xMin]; set b [expr {$a + $m6pa_s}]
  } else {
    set b [$m6pa_die xMax]; set a [expr {$b - $m6pa_s}]
  }
  set cursor [$m6pa_die yMin]
  foreach span [lsort -integer -index 0 [dict get $m6pa_spans $face]] {
    lassign $span y0 y1
    if {$y0 > $cursor} { lappend m6pa_rects [list $a $cursor $b $y0] }
    set cursor [expr {max($cursor, $y1)}]
  }
  if {$cursor < [$m6pa_die yMax]} { lappend m6pa_rects [list $a $cursor $b [$m6pa_die yMax]] }
}
set m6pa_have [dict create]
foreach o [$m6pa_blk getObstructions] {
  set bx [$o getBBox]
  if {[[$bx getTechLayer] getName] ne "M6"} continue
  set r [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
  if {$r in $m6pa_rects} { dict lappend m6pa_have $r $o }
}
set m6pa_count 0
foreach r $m6pa_rects {
  if {$::ot_m6_pin_access_mode eq "remove"} {
    if {[dict exists $m6pa_have $r]} {
      foreach o [dict get $m6pa_have $r] { odb::dbObstruction_destroy $o; incr m6pa_count }
    }
  } elseif {![dict exists $m6pa_have $r]} {
    set o [odb::dbObstruction_create $m6pa_blk $m6pa_l {*}$r]
    # This is a route exclusion, not physical metal. Zero spacing allows a
    # terminal-contained landing to touch the exclusion's exact boundary.
    $o setMinSpacing 0
    incr m6pa_count
  }
}
puts "OT_M6_PIN_ACCESS $::ot_m6_pin_access_mode $m6pa_count obstruction(s); deepened $m6pa_n E/W M6 pins to $::ot_m6_stub_um um"
}
ot_m6_pin_access_apply
