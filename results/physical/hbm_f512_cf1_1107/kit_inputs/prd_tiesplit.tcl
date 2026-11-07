# DIE-S81-54/ECO 11-04: split long tie nets, one tie per load except the nearest. The resizer cannot buffer a tie net
# (half: TIELOx1 -> 5 ICG/SE over 230 um, slew 352). Constant value unchanged. Selected by geometry, not by STA, because
# a netlist edit after the routed SPEF read stops repair_design with EST-0104. Sourced before that read, targeted mode
# only. OT_PRD_TIE_SPLIT=0 = off; OT_PRD_TIE_SPAN_UM = minimum net half-perimeter (default 60).
proc ot_prd_tie_split {} {
  set block [ord::get_db_block]
  set dbu [$block getDbUnitsPerMicron]
  set span [expr {[info exists ::env(OT_PRD_TIE_SPAN_UM)] ? $::env(OT_PRD_TIE_SPAN_UM) : 60}]
  set split 0; set made 0
  set ::ot_prd_tie_drivers {}
  foreach net [$block getNets] {
    if {[$net getSigType] ne "SIGNAL"} continue
    set drv {}; set loads {}
    foreach it [$net getITerms] {
      if {[$it isOutputSignal]} { lappend drv $it } elseif {[$it isInputSignal]} { lappend loads $it }
    }
    if {[llength $drv] != 1 || [llength $loads] < 2} continue
    set dinst [[lindex $drv 0] getInst]
    set master [$dinst getMaster]
    if {![string match TIE* [$master getName]]} continue
    lassign [$dinst getLocation] dx dy
    set x0 $dx; set x1 $dx; set y0 $dy; set y1 $dy
    set best {}; set bestd -1
    foreach l $loads {
      lassign [[$l getInst] getLocation] x y
      set x0 [expr {min($x0, $x)}]; set x1 [expr {max($x1, $x)}]
      set y0 [expr {min($y0, $y)}]; set y1 [expr {max($y1, $y)}]
      set d [expr {abs($x - $dx) + abs($y - $dy)}]
      if {$bestd < 0 || $d < $bestd} { set best $l; set bestd $d }
    }
    if {($x1 - $x0 + $y1 - $y0) < $span * $dbu} continue
    set out [[[lindex $drv 0] getMTerm] getName]
    foreach l $loads {
      if {$l eq $best} continue
      set n 0
      while {[$block findInst ot_prd_tie_$n] ne "NULL"} { incr n }
      set ti [odb::dbInst_create $block $master ot_prd_tie_$n]
      set nn [odb::dbNet_create $block ot_prd_tie_${n}_n]
      lassign [[$l getInst] getLocation] x y
      $ti setLocation $x $y
      $ti setPlacementStatus PLACED
      [$ti findITerm $out] connect $nn
      lappend ::ot_prd_tie_drivers [$ti findITerm $out]
      # a gated-clock cell load is dont_touch: its data pin moves, the cell stays LOCKED
      set li [$l getInst]; set ldt [$li isDoNotTouch]
      $li setDoNotTouch 0
      $l disconnect
      $l connect $nn
      $li setDoNotTouch $ldt
      incr made
    }
    lappend ::ot_prd_tie_drivers [lindex $drv 0]
    incr split
  }
  puts "OT_PRD_TARGETED tie nets split $split, tie cells added $made"
}
# GRT indexes nets when global_route -start_incremental runs from those with guides; a net created before that, with no guide, is
# unknown to it, and reconnecting a pin does not add it (half3, bf_col3c3: the new tie nets ended with no guide, have_routes 0).
# So recreate each new tie net inside the window: the create callback adds it. Same name, same pins.
proc ot_prd_tie_mark_dirty {} {
  set block [ord::get_db_block]; set again 0
  foreach it $::ot_prd_tie_drivers {
    set net [$it getNet]; set name [$net getName]
    if {![string match ot_prd_tie_*_n $name]} {
      set inst [$it getInst]; set dt [$inst isDoNotTouch]
      $inst setDoNotTouch 0
      $it disconnect
      $it connect $net
      $inst setDoNotTouch $dt
      continue
    }
    set pins [$net getITerms]; set dts {}
    foreach p $pins { set i [$p getInst]; lappend dts [$i isDoNotTouch]; $i setDoNotTouch 0; $p disconnect }
    odb::dbNet_destroy $net
    set nn [odb::dbNet_create $block $name]
    foreach p $pins d $dts { $p connect $nn; [$p getInst] setDoNotTouch $d }
    incr again
  }
  puts "OT_PRD_TARGETED tie nets marked dirty [llength $::ot_prd_tie_drivers], recreated $again"
}
# Off (OT_PRD_TIE_SPLIT=0) still defines the list: prd_hook calls ot_prd_tie_mark_dirty whenever this file was sourced
# (nf1 h1 11-05: global_route.tcl 191 cannot read ::ot_prd_tie_drivers).
set ::ot_prd_tie_drivers {}
if {![info exists ::env(OT_PRD_TIE_SPLIT)] || $::env(OT_PRD_TIE_SPLIT) ne "0"} { ot_prd_tie_split }
