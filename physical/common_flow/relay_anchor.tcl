# PRE_GLOBAL_PLACE hook (HBM-HC7-DBK 2026-10-20): LANDED relay / landing flops FIRM at their planned station, before
# io_flop_at_pins.tcl (spec "pin_hook_before_flops"; a FIRM flop is kept there) and released for DPL by
# relay_anchor_release.tcl (spec "pre_dpl_extra").  Placement only: 0 cycles, no netlist / SDC change.
# Why: a relay register cuts a long single-cycle wire only if it SITS on the wire.  Timing-driven GPL is free to put a
# 2-pin relay anywhere in the bounding box of its two pins (equal HPWL), so a hard-child -> relay -> hard-child hop can
# still carry the whole span on one side (Codex dbk_cpl review 10-20: buffer-transparent reach 713 / 455 / 456 um).
# Table OT_RLY_ANCHOR (repo file, one rule per line, '#' comments; rules apply in order, each must match >= 1 flop):
#   <regexp> xy <x_um> <y_um>      every matching flop at that point (die coordinates)
#   <regexp> mid <frac>            every matching flop at frac of the way from its D source to the centroid of its Q
#                                  sinks (Manhattan: x and y split by the same fraction, so each side gets frac / 1-frac
#                                  of the span).  Source / sinks are found through <= OT_RLY_HOPS (8) single-input
#                                  INV / BUF cells: an input port, a hard-child (BLOCK) pin, or a flop already FIRM from
#                                  an earlier rule; sinks: output ports and hard-child pins (flops FIRM earlier count).
# <regexp> is matched against the instance name with the backslash escapes removed (u_dbk.L[7].cv_q$_DFF_P_).
# Overlaps and macro / blockage sites are resolved by anchor_row_packing.tcl (nearest legal free row site).
# The planned and packed position of every flop goes to $RESULTS_DIR/ot_relay_anchor.tsv; names to ot_relay_anchor.txt.
set ot_ra_blk [ord::get_db_block]
set ot_ra_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_ra_core [$ot_ra_blk getCoreArea]
set ot_ra_hops [expr {[info exists ::env(OT_RLY_HOPS)] && $::env(OT_RLY_HOPS) ne "" ? $::env(OT_RLY_HOPS) : 8}]
if {![info exists ::env(OT_RLY_ANCHOR)] || ![file exists $::env(OT_RLY_ANCHOR)]} {
  error "OT_RLY_ANCHOR: table missing ([expr {[info exists ::env(OT_RLY_ANCHOR)] ? $::env(OT_RLY_ANCHOR) : {unset}}])"
}
proc ot_ra_isff {inst} { set m [[$inst getMaster] getName]; expr {[string match "DFF*" $m] || [string match "ASYNC_DFF*" $m]} }
proc ot_ra_isbuf {inst} { set m [[$inst getMaster] getName]; expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]} }
proc ot_ra_center {inst dbu} {
  set b [$inst getBBox]
  return [list [expr {double([$b xMin] + [$b xMax]) / 2.0 / $dbu}] [expr {double([$b yMin] + [$b yMax]) / 2.0 / $dbu}]]
}
proc ot_ra_bt_xy {bt dbu} {
  set bb [$bt getBBox]
  return [list [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]]
}
proc ot_ra_it_xy {it dbu} {
  set v [$it getAvgXY]
  if {![lindex $v 0]} { return "" }
  return [list [expr {double([lindex $v 1]) / $dbu}] [expr {double([lindex $v 2]) / $dbu}]]
}
# fixed point driving net (through single-input INV / BUF), or ""
proc ot_ra_src {net hops dbu} {
  for {set h 0} {$h <= $hops} {incr h} {
    if {$net eq "" || $net eq "NULL"} { return "" }
    foreach bt [$net getBTerms] { if {[$bt getIoType] eq "INPUT"} { return [ot_ra_bt_xy $bt $dbu] } }
    set drv ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it } }
    if {$drv eq ""} { return "" }
    set inst [$drv getInst]
    if {[[$inst getMaster] isBlock]} { return [ot_ra_it_xy $drv $dbu] }
    if {[ot_ra_isff $inst]} { if {[$inst isFixed]} { return [ot_ra_center $inst $dbu] }; return "" }
    if {![ot_ra_isbuf $inst]} { return "" }
    set net ""
    foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set net [$it getNet] } }
  }
  return ""
}
# fixed sink points of net (through INV / BUF trees)
proc ot_ra_sinks {net hops dbu} {
  set pts {}
  if {$net eq "" || $net eq "NULL" || $hops < 0} { return $pts }
  foreach bt [$net getBTerms] { if {[$bt getIoType] eq "OUTPUT"} { lappend pts [ot_ra_bt_xy $bt $dbu] } }
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    if {[[$inst getMaster] isBlock]} { set p [ot_ra_it_xy $it $dbu]; if {$p ne ""} { lappend pts $p }; continue }
    if {[ot_ra_isff $inst]} { if {[$inst isFixed]} { lappend pts [ot_ra_center $inst $dbu] }; continue }
    if {[ot_ra_isbuf $inst]} {
      foreach ot [$inst getITerms] {
        if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend pts {*}[ot_ra_sinks [$ot getNet] [expr {$hops - 1}] $dbu] }
      }
    }
  }
  return $pts
}
proc ot_ra_place {inst x y blk dbu} {
  set core [$blk getCoreArea]
  set w [expr {double([[$inst getMaster] getWidth]) / $dbu}]; set h [expr {double([[$inst getMaster] getHeight]) / $dbu}]
  set cx0 [expr {double([$core xMin]) / $dbu}]; set cx1 [expr {double([$core xMax]) / $dbu}]
  set cy0 [expr {double([$core yMin]) / $dbu}]; set cy1 [expr {double([$core yMax]) / $dbu}]
  set x [expr {min(max($x - $w / 2.0, $cx0), $cx1 - $w)}]
  set y [expr {min(max($y - $h / 2.0, $cy0), $cy1 - $h)}]
  set y [expr {$cy0 + round(($y - $cy0) / $h) * $h}]
  $inst setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
  $inst setPlacementStatus FIRM
}
# flops by unescaped name
set ot_ra_ffs {}
foreach inst [$ot_ra_blk getInsts] { if {[ot_ra_isff $inst]} { lappend ot_ra_ffs [list [string map {\\ {}} [$inst getName]] $inst] } }
set ot_ra_list {}; set ot_ra_rows {}
set fh [open $::env(OT_RLY_ANCHOR) r]; set ot_ra_lines [split [read $fh] "\n"]; close $fh
foreach line $ot_ra_lines {
  set line [string trim $line]
  if {$line eq "" || [string index $line 0] eq "#"} continue
  set re [lindex $line 0]; set mode [lindex $line 1]
  set n 0
  foreach pair $ot_ra_ffs {
    lassign $pair name inst
    if {![regexp -- $re $name] || [$inst isFixed]} continue
    if {$mode eq "xy"} {
      set px [lindex $line 2]; set py [lindex $line 3]; set span 0.0; set sx $px; set sy $py; set kx $px; set ky $py
    } elseif {$mode eq "mid"} {
      set frac [lindex $line 2]
      set dnet ""; set qnets {}
      foreach it [$inst getITerms] {
        set mt [[$it getMTerm] getName]
        if {$mt eq "D"} { set dnet [$it getNet] }
        if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { lappend qnets [$it getNet] }
      }
      set s [ot_ra_src $dnet $ot_ra_hops $ot_ra_dbu]
      set pts {}
      foreach q $qnets { lappend pts {*}[ot_ra_sinks $q $ot_ra_hops $ot_ra_dbu] }
      if {$s eq "" || ![llength $pts]} { error "OT_RLY_ANCHOR: $name ($re mid) has no fixed source / sink (src '$s', [llength $pts] sinks)" }
      lassign $s sx sy
      set kx 0.0; set ky 0.0
      foreach p $pts { set kx [expr {$kx + [lindex $p 0]}]; set ky [expr {$ky + [lindex $p 1]}] }
      set kx [expr {$kx / [llength $pts]}]; set ky [expr {$ky / [llength $pts]}]
      set px [expr {$sx + $frac * ($kx - $sx)}]; set py [expr {$sy + $frac * ($ky - $sy)}]
      set span [expr {abs($kx - $sx) + abs($ky - $sy)}]
    } else { error "OT_RLY_ANCHOR: unknown mode '$mode' in: $line" }
    ot_ra_place $inst $px $py $ot_ra_blk $ot_ra_dbu
    lappend ot_ra_list [$inst getName]
    lappend ot_ra_rows [list [$inst getName] $re $mode $sx $sy $kx $ky $span $px $py]
    incr n
  }
  if {$n == 0} { error "OT_RLY_ANCHOR: rule matched no flop: $line" }
  puts [format "OT_RLY_ANCHOR %-48s %-3s %4d flops" $re $mode $n]
}
if {[llength $ot_ra_list]} {
  set ot_anchor_script /src/physical/common_flow/anchor_row_packing.tcl
  if {![file exists $ot_anchor_script] && [info script] ne ""} {
    set ot_anchor_script [file join [file dirname [info script]] anchor_row_packing.tcl]
  }
  source $ot_anchor_script
  ot_anchor_pack::repair $ot_ra_blk $ot_ra_list
}
set fh [open $::env(RESULTS_DIR)/ot_relay_anchor.txt w]; foreach n $ot_ra_list { puts $fh $n }; close $fh
set fh [open $::env(RESULTS_DIR)/ot_relay_anchor.tsv w]
puts $fh "inst\trule\tmode\tsrc_x\tsrc_y\tsink_x\tsink_y\tspan_um\tplan_x\tplan_y\tfinal_x\tfinal_y"
set ot_ra_disp 0.0
foreach r $ot_ra_rows {
  set inst [$ot_ra_blk findInst [lindex $r 0]]
  lassign [ot_ra_center $inst $ot_ra_dbu] fx fy
  set ot_ra_disp [expr {max($ot_ra_disp, abs($fx - [lindex $r 8]) + abs($fy - [lindex $r 9]))}]
  puts $fh [join [concat $r [list [format %.3f $fx] [format %.3f $fy]]] "\t"]
}
close $fh
puts [format "OT_RLY_ANCHOR placed %d relay / landing flops FIRM (max packing displacement %.1f um)" [llength $ot_ra_list] $ot_ra_disp]
