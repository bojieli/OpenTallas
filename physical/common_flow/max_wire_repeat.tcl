# POST_RESIZE hook (S81-CAPC slew, 2026-10-19; spec orfs_vars POST_RESIZE_TCL=physical/common_flow/max_wire_repeat.tcl):
# NO LONG SINGLE-DRIVER WIRE.  Routed CAPC a62 (s81sl_capc_p1_die_rc_order) closed timing (TT +326.31 / FF +17.43) but the
# final TT electrical report had two max-slew violators, 300.71 / 275.63 ps > 260: net2389 (pin register g_pin.wq[27] ->
# BUFx3 place2390 -> 157 um -> INVx1 _1653_ -> child u_tw rt[27]) and nd[0] (child u_rt ETM output cw_n_d[0] -> 135 um ->
# BUFx3 place2292 -> output pin register cw_n_d[0]); routed R 4.2-5.0 kOhm, C 25-27 fF.  Placement and post-GRT
# repair_design (slew margin 30 %) had passed both: the resizer's default wire limit left 677 single-driver nets of
# 120-165 um, and routed RC on such a net can exceed the placement estimate by more than the margin.  The structural fix
# is a repeated wire everywhere: after the ORFS 3_4 repair_design, repair_design again with -max_wire_length
# OT_MAX_WIRE_UM (default 80 um, ~1/5 of the 405 um registered reach), so every signal net is a short driven segment
# whatever its routed layer / detour; the gate's GATE_LONGNET check (spec max_signal_net_um) proves it after CTS.
# Clock nets are untouched (repair_design skips them; CTS runs later).  Repeaters that land on a hard child (Steiner
# points over a macro) are SNAPPED to the nearest point just outside that child's halo, every other cell stays where
# it is; DPL then legalises locally.  (Gate 1, 10-19 11:33: sourcing post_resize_relocate.tcl instead ran an
# incremental GLOBAL placement that re-spread all 15.5k cells and undid the segmentation: max net 220 um, 45 slew
# violators after CTS.)  No constraint, limit or margin is changed.
set ot_mw_um 80
if {[info exists ::env(OT_MAX_WIRE_UM)] && $::env(OT_MAX_WIRE_UM) ne ""} { set ot_mw_um $::env(OT_MAX_WIRE_UM) }
estimate_parasitics -placement
set ot_mw_n0 [sta::network_leaf_instance_count]
set ot_mw_args [list -verbose -max_wire_length $ot_mw_um]
if {[info exists ::env(SLEW_MARGIN)] && $::env(SLEW_MARGIN) ne ""} { lappend ot_mw_args -slew_margin $::env(SLEW_MARGIN) }
if {[info exists ::env(CAP_MARGIN)] && $::env(CAP_MARGIN) ne ""} { lappend ot_mw_args -cap_margin $::env(CAP_MARGIN) }
repair_design {*}$ot_mw_args
puts "OT_MAXWIRE repair_design -max_wire_length $ot_mw_um um: leaf instances $ot_mw_n0 -> [sta::network_leaf_instance_count]"
set ot_mw_blk [ord::get_db_block]
set ot_mw_dbu [$ot_mw_blk getDbUnitsPerMicron]
set ot_mw_halo 5.4
if {[info exists ::env(OT_MAX_WIRE_HALO_UM)] && $::env(OT_MAX_WIRE_HALO_UM) ne ""} { set ot_mw_halo $::env(OT_MAX_WIRE_HALO_UM) }
set ot_mw_m [expr {int(($ot_mw_halo + 0.6) * $ot_mw_dbu)}]
set ot_mw_rr {}
foreach ot_i [$ot_mw_blk getInsts] {
  if {[[$ot_i getMaster] isBlock]} {
    set b [$ot_i getBBox]
    lappend ot_mw_rr [list [expr {[$b xMin] - $ot_mw_m}] [expr {[$b yMin] - $ot_mw_m}] [expr {[$b xMax] + $ot_mw_m}] [expr {[$b yMax] + $ot_mw_m}]]
  }
}
set ot_mw_core [$ot_mw_blk getCoreArea]
proc ot_mw_inside {x y rr} {
  foreach r $rr { lassign $r a c e f; if {$x >= $a && $x <= $e && $y >= $c && $y <= $f} { return 1 } }
  return 0
}
set ot_mw_snap 0; set ot_mw_stuck 0; set ot_mw_dmax 0
foreach ot_i [$ot_mw_blk getInsts] {
  set ms [$ot_i getMaster]
  if {[$ms isBlock] || [$ot_i isFixed] || [$ms getType] ne "CORE"} continue
  set b [$ot_i getBBox]
  set x [expr {([$b xMin] + [$b xMax]) / 2}]; set y [expr {([$b yMin] + [$b yMax]) / 2}]
  if {![ot_mw_inside $x $y $ot_mw_rr]} continue
  set best {}
  foreach r $ot_mw_rr {
    lassign $r a c e f
    if {!($x >= $a && $x <= $e && $y >= $c && $y <= $f)} continue
    foreach cand [list [list [expr {$a - 1}] $y] [list [expr {$e + 1}] $y] [list $x [expr {$c - 1}]] [list $x [expr {$f + 1}]]] {
      lassign $cand nx ny
      if {$nx < [$ot_mw_core xMin] || $nx > [$ot_mw_core xMax] || $ny < [$ot_mw_core yMin] || $ny > [$ot_mw_core yMax]} continue
      if {[ot_mw_inside $nx $ny $ot_mw_rr]} continue
      set d [expr {abs($nx - $x) + abs($ny - $y)}]
      if {$best eq "" || $d < [lindex $best 0]} { set best [list $d $nx $ny] }
    }
  }
  if {$best eq ""} { incr ot_mw_stuck; continue }
  lassign $best d nx ny
  $ot_i setLocation [expr {$nx - [$ms getWidth] / 2}] [expr {$ny - [$ms getHeight] / 2}]
  $ot_i setPlacementStatus PLACED
  incr ot_mw_snap
  if {$d > $ot_mw_dmax} { set ot_mw_dmax $d }
}
puts [format "OT_MAXWIRE snapped %d cells off hard children (halo %.2f um), max move %.1f um, %d with no free side" $ot_mw_snap $ot_mw_halo [expr {double($ot_mw_dmax) / $ot_mw_dbu}] $ot_mw_stuck]
if {$ot_mw_stuck > 0} { error "OT_MAXWIRE: $ot_mw_stuck cells inside hard children have no free side" }
# A wire that crosses a hard child cannot be repeated over it (no rows there): its span is the child side + two halos
# (u_rt 116.64 + 2 x 6 = 128.6 um in gate 2).  Such a net gets the STRONGEST buffer of its driver's function at its source,
# kept (dont_touch) so later repair cannot down-size it.  Only BUF/INV standard-cell drivers are resized.
set ot_mw_long [expr {$ot_mw_um * 1.25 * $ot_mw_dbu}]
set ot_mw_up 0; set ot_mw_upf 0
set ot_mw_pg [expr {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"}]
# PG before protection in BOTH modes (S81-CAPC3 10-19): global_connect skips dont_touch insts (dbGlobalConnect.cpp:163),
# so a driver protected here stays unbound unless it is bound first.  Strict: per-instance source-owned binder; standard:
# the design's own global_connect rules once for the whole batch (ot_pg_standard_bind, main 67cb1acc7), then protect.
set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
source $ot_pg_helper
set ot_mw_protect {}
foreach ot_n [$ot_mw_blk getNets] {
  if {[$ot_n getSigType] ne "SIGNAL" || [$ot_n isSpecial]} continue
  set drv {}; set lds {}
  foreach it [$ot_n getITerms] {
    if {[$it isOutputSignal]} { lappend drv $it } elseif {[$it isInputSignal]} { lappend lds $it }
  }
  if {[llength $drv] != 1 || [llength $lds] == 0} continue
  set di [[lindex $drv 0] getInst]
  set dm [[$di getMaster] getName]
  if {![regexp {^(BUF|INV)} $dm -> fn]} continue
  set db [$di getBBox]; set dx [expr {([$db xMin] + [$db xMax]) / 2}]; set dy [expr {([$db yMin] + [$db yMax]) / 2}]
  set far 0
  foreach it $lds { set lb [[$it getInst] getBBox]; set d [expr {abs(([$lb xMin] + [$lb xMax]) / 2 - $dx) + abs(([$lb yMin] + [$lb yMax]) / 2 - $dy)}]; if {$d > $far} { set far $d } }
  if {$far <= $ot_mw_long} continue
  set done 0
  foreach cand [expr {$fn eq "BUF" ? {BUFx16f_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx10_ASAP7_75t_R} : {INVx13_ASAP7_75t_R INVx11_ASAP7_75t_R}}] {
    if {$cand eq $dm} { set done 1; break }
    if {[llength [get_lib_cells -quiet */$cand]] == 0} continue
    if {![catch {replace_cell [$di getName] [lindex [get_lib_cells */$cand] 0]}]} { set done 1; break }
  }
  if {$done} { lappend ot_mw_protect $di; incr ot_mw_up } else { incr ot_mw_upf }
}
if {[llength $ot_mw_protect]} {
  if {$ot_mw_pg} {
    set ot_mw_pg_map [ot_pg_prepare $ot_mw_blk]
    foreach di $ot_mw_protect { ot_pg_bind_before_protect $ot_mw_pg_map $di }
  } else {
    ot_pg_standard_bind max_wire_repeat
  }
  foreach di $ot_mw_protect {
    foreach row [ot_pg_master_census $di] {
      lassign $row mt term why
      if {$why ne "" || [$term getNet] eq "NULL"} { error "OT_MAXWIRE_PG_UNBOUND_BEFORE_PROTECT [$di getName]/[$mt getName] $why" }
    }
    $di setDoNotTouch 1
  }
}
puts [format "OT_MAXWIRE kept strong source drivers on %d nets > %.1f um (child crossings), %d not resizable" $ot_mw_up [expr {double($ot_mw_long) / $ot_mw_dbu}] $ot_mw_upf]
estimate_parasitics -placement
