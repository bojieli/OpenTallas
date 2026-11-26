# GENERATED-KIT HOOK tools/die_plan/gpl_td.tcl (C-GPL-TD-INFLATION 11-26, CLASS-OWNERS-B; plan flag gpl_td, default OFF).
# Sourced at the end of face_flops.tcl (PRE_GLOBAL_PLACE, after the OT_GPL_GUARD) and at the end of face_flops_release.tcl
# (PRE_DETAIL_PLACE) only when the plan carries gpl_td.  Three parts, one per plan key:
#  top_overflow_trigger (env OT_GPL_TD_TOP = settle overflow S, 0 = off): timing-driven GPL repair must fire on the TOP-LEVEL overflow.
#     OpenROAD tests the timing-driven trigger on the MEAN overflow of the top-level region and every odb region/group; tiny
#     regions (OT_LOGIC_CLUSTER, place_regions) finish at once, so the mean falls under the first reweight threshold (0.64) at
#     iteration 1 while the top-level overflow is still 0.73 (HEAD hd_lep0N fed00: trigger read 0.185, 56,515 repair buffers on
#     an unsettled placement, HPWL 1.30e7 -> 1.90e7).  The wrapper splits a timing-driven call in two: phase 1 is the same call
#     without any timing-driven key, stopped at -overflow S (regions are finished by then, so the mean IS the top-level overflow);
#     phase 2 is the same call -incremental (no initial placement) whose only reweight threshold is S, so the repair runs once,
#     on a placement that has settled, and the placement then continues to the call's own exit overflow.
#  firm_small_clusters: see logic_cluster.py (small OT_LOGIC_CLUSTER cells are seated FIRM, never a GPL region).
#  cell_growth_gate (env OT_GPL_TD_GROWTH = 1 report, 2 fail): the non-tap standard cell count after global placement and after the
#     place resize (this file again at PRE_DETAIL_PLACE, ::ot_gpl_td_release) must stay under min(OT_CELL_CENSUS_CAP, pre-GPL count x (1 + OT_GPL_TD_GROWTH_REL)).
#     One loud line per stage: OT_GPL_TD_GROWTH stage=... pre=... now=... bound=... growth=...: OK | FLAG | FAIL.
proc ot_gpl_td_nontap {} {
  set n 0
  foreach i [[ord::get_db_block] getInsts] {
    set m [$i getMaster]
    if {[$m isBlock]} continue
    if {[regexp {^(TAPCELL|ENDCAP|FILLER|FILL|DECAP)} [$m getName]]} continue
    incr n
  }
  return $n
}
proc ot_gpl_td_pre_file {} { return [file join $::env(RESULTS_DIR) ot_gpl_td_pre.txt] }
proc ot_gpl_td_growth_mode {} {
  if {![info exists ::env(OT_GPL_TD_GROWTH)] || $::env(OT_GPL_TD_GROWTH) eq ""} { return 0 }
  if {$::env(OT_GPL_TD_GROWTH) ni {0 1 2}} { error "OT_GPL_TD_GROWTH must be 0, 1 (report) or 2 (fail), got '$::env(OT_GPL_TD_GROWTH)'" }
  return $::env(OT_GPL_TD_GROWTH)
}
proc ot_gpl_td_growth_record {} {
  if {[ot_gpl_td_growth_mode] == 0} return
  set n [ot_gpl_td_nontap]
  set f [open [ot_gpl_td_pre_file] w]; puts $f $n; close $f
  puts "OT_GPL_TD_GROWTH stage=pre_gpl nontap=$n"
}
proc ot_gpl_td_growth_gate {stage} {
  set mode [ot_gpl_td_growth_mode]
  if {$mode == 0} return
  if {![file exists [ot_gpl_td_pre_file]]} { puts "OT_GPL_TD_GROWTH stage=$stage WARN no pre-GPL count (ot_gpl_td_pre.txt)"; return }
  set f [open [ot_gpl_td_pre_file] r]; set pre [string trim [read $f]]; close $f
  set cap 400000
  if {[info exists ::env(OT_CELL_CENSUS_CAP)] && [string is integer -strict $::env(OT_CELL_CENSUS_CAP)]} { set cap $::env(OT_CELL_CENSUS_CAP) }
  set rel 0.35
  if {[info exists ::env(OT_GPL_TD_GROWTH_REL)] && [string is double -strict $::env(OT_GPL_TD_GROWTH_REL)]} { set rel $::env(OT_GPL_TD_GROWTH_REL) }
  set bound [expr {min($cap, int($pre * (1.0 + $rel)))}]
  set now [ot_gpl_td_nontap]
  set growth [expr {$pre > 0 ? double($now - $pre) / $pre : 0.0}]
  set verdict OK
  if {$now > $bound} { set verdict [expr {$mode == 2 ? "FAIL" : "FLAG"}] }
  puts [format "OT_GPL_TD_GROWTH stage=%s pre=%d now=%d bound=%d growth=%.3f: %s" $stage $pre $now $bound $growth $verdict]
  if {$verdict eq "FAIL"} { error "OT_GPL_TD_GROWTH stage=$stage: non-tap cells $now exceed the bound $bound (pre-GPL $pre, cap $cap, rel $rel)" }
}
# global_placement arguments without any timing-driven key (routability and the rest are kept)
proc ot_gpl_td_strip_args {argl} {
  set out {}
  set n [llength $argl]
  for {set k 0} {$k < $n} {incr k} {
    set a [lindex $argl $k]
    if {$a in {-timing_driven -timing_driven_repair_timing -virtual_cts}} continue
    if {[regexp {^-(timing_driven_|keep_resize_below_overflow$|virtual_cts_)} $a]} { incr k; continue }
    lappend out $a
  }
  return $out
}
proc ot_gpl_td_top_value {} {
  if {![info exists ::env(OT_GPL_TD_TOP)] || $::env(OT_GPL_TD_TOP) eq ""} { return 0 }
  set v $::env(OT_GPL_TD_TOP)
  if {![string is double -strict $v] || $v < 0 || $v >= 1} { error "OT_GPL_TD_TOP must be 0 (off) or a settle overflow in (0, 1), got '$v'" }
  return $v
}
proc ot_gpl_td_opt {argl key} {
  set k [lsearch -exact $argl $key]
  if {$k < 0} { return {} }
  return [lindex $argl [expr {$k + 1}]]
}
proc ot_gpl_td_set {argl key val} {
  set k [lsearch -exact $argl $key]
  if {$k < 0} { return [concat $argl [list $key $val]] }
  return [lreplace $argl [expr {$k + 1}] [expr {$k + 1}] $val]
}
proc ot_gpl_td_wrapped {args} {
  set s [ot_gpl_td_top_value]
  set prev $::ot_gpl_td_prev
  set growth [expr {[ot_gpl_td_growth_mode] > 0}]
  if {$growth} { ot_gpl_td_growth_record }
  if {$s <= 0 || [lsearch -exact $args -timing_driven] < 0} {
    set rc [uplevel 1 [list {*}$prev {*}$args]]
    if {$growth} { ot_gpl_td_growth_gate post_gpl }
    return $rc
  }
  # settle overflow: never above the call's own keep threshold, else the repair would run on the settled placement and be discarded
  set keep [ot_gpl_td_opt $args -keep_resize_below_overflow]
  if {[string is double -strict $keep] && $keep > 0 && $keep < $s} { set s $keep }
  set exit [ot_gpl_td_opt $args -overflow]
  if {[string is double -strict $exit] && $exit >= $s} {
    puts "OT_GPL_TD_TOP exit overflow $exit >= settle overflow $s: no settled placement to repair on, call unchanged"
    set rc [uplevel 1 [list {*}$prev {*}$args]]
    if {$growth} { ot_gpl_td_growth_gate post_gpl }
    return $rc
  }
  set p1 [ot_gpl_td_set [ot_gpl_td_strip_args $args] -overflow $s]
  set p2 {}
  foreach a $args { if {$a ne "-force_center_initial_place"} { lappend p2 $a } }
  set p2 [concat [list -incremental] $p2]
  set thr [expr {int(round(100.0 * $s))}]
  set have [ot_gpl_td_opt $p2 -timing_driven_net_reweight_overflow]
  set keepl {}
  foreach t $have { if {$t <= $thr} { lappend keepl $t } }
  if {![llength $keepl]} { set keepl [list $thr] }
  set p2 [ot_gpl_td_set $p2 -timing_driven_net_reweight_overflow $keepl]
  puts "OT_GPL_TD_TOP phase 1 (no timing-driven keys, stop at overflow $s): $p1"
  set ::ot_gpl_td_phase 1
  set rc [uplevel 1 [list {*}$prev {*}$p1]]
  puts "OT_GPL_TD_TOP phase 2 (incremental, timing-driven reweight at $keepl): $p2"
  set rc [uplevel 1 [list {*}$prev {*}$p2]]
  unset -nocomplain ::ot_gpl_td_phase
  if {$growth} { ot_gpl_td_growth_gate post_gpl }
  return $rc
}
if {![info exists ::ot_gpl_td_release] && [info commands ::global_placement] ne "" && [info commands ::ot_gpl_td_native] eq "" && ![info exists ::ot_gpl_td_prev]} {
  set ot_gpl_td_alias [interp alias {} ::global_placement]
  if {$ot_gpl_td_alias ne ""} {
    set ::ot_gpl_td_prev $ot_gpl_td_alias
  } else {
    rename ::global_placement ::ot_gpl_td_native
    set ::ot_gpl_td_prev ::ot_gpl_td_native
  }
  interp alias {} ::global_placement {} ::ot_gpl_td_wrapped
}
# PRE_DETAIL_PLACE (face_flops_release.tcl) sources this file with ::ot_gpl_td_release set, then calls ot_gpl_td_growth_gate post_resize
