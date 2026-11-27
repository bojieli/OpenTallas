# GENERATED-KIT HOOK tools/die_plan/gpl_td.tcl (C-GPL-TD-INFLATION 11-26, CLASS-OWNERS-B; plan flag gpl_td, default OFF).
# Sourced at the end of face_flops.tcl (PRE_GLOBAL_PLACE, after the OT_GPL_GUARD) and at the end of face_flops_release.tcl
# (PRE_DETAIL_PLACE) only when the plan carries gpl_td.  Three parts, one per plan key:
#  top_overflow_trigger (env OT_GPL_TD_TOP = settle overflow S, 0 = off): timing-driven GPL repair fires only on a SETTLED placement.
#     OpenROAD tests the timing-driven trigger on the MEAN overflow of the top-level region and every odb region/group (log:
#     "GPL-0101 Iter 1, overflow 0.185" while the top-level overflow was 0.7317, 15 regions of 3-20 cells), and its default first reweight
#     threshold is 0.64, so on a sparse design the first repair_design runs at iteration 1..170 on an unspread placement and every long
#     wire gets repeaters (HEAD hd_lep0N fed00 +56,515 buffers, HPWL 1.30e7 -> 1.90e7; hd_lep0N_w pass 1 at 0.635: +20,234; HEAD has no
#     GPL_KEEP_OVERFLOW).  The engine cannot be told to read the top-level overflow (a two-phase run was measured and rejected: OpenROAD
#     -incremental skips a fully placed design, and -skip_initial_place restarts Nesterov, the overflow climbs back 0.31 -> 0.66 and the
#     whole spread is repeated).  So the wrapper keeps ONE call and keeps only the call's -timing_driven_net_reweight_overflow thresholds at or
#     under S (the single threshold S when the call names none or none qualifies), after
#     firm_small_clusters has removed the tiny regions that made the mean read low.  A call whose exit overflow is >= S would never reach
#     a pass: the threshold becomes exit + 5 points (the sparse-exit rule of OT_GPL_GUARD (3)).
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
  if {$s > 0 && [lsearch -exact $args -timing_driven] >= 0} {
    # the settle overflow never exceeds the call's own keep threshold (a pass above it would run and be discarded)
    set keep [ot_gpl_td_opt $args -keep_resize_below_overflow]
    if {[string is double -strict $keep] && $keep > 0 && $keep < $s} { set s $keep }
    set exit [ot_gpl_td_opt $args -overflow]
    if {[string is double -strict $exit] && $exit >= $s} { set s [expr {$exit + 0.05}] }
    set thr [expr {int(round(100.0 * $s))}]
    set have [ot_gpl_td_opt $args -timing_driven_net_reweight_overflow]
    set keepl {}
    foreach t $have { if {$t <= $thr} { lappend keepl $t } }
    if {![llength $keepl]} { set keepl [list $thr] }
    set args [ot_gpl_td_set $args -timing_driven_net_reweight_overflow $keepl]
    puts "OT_GPL_TD_TOP timing-driven repair only at overflow <= $s (reweight thresholds $keepl): $args"
  }
  set rc [uplevel 1 [list {*}$prev {*}$args]]
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
