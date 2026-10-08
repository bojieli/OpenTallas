# OpenTallas FLOW-HOLD (2026-10-07): multi-mode route-time hold repair.  SS setup + FF hold are BOTH active when ORFS
# repairs timing at CTS and after global route (repair_timing_helper), each corner under its own constraints.
#
# Why: the closure loop repaired hold at the primary (SS) corner only (OT_ROUTE_HOLD_CORNERS=primary), because the one
# route SDC carries an SS-insertion IO model that is fake at FF.  A hold requirement is an ABSOLUTE time (25 ps hold
# uncertainty + the die IO hold term + t_hold), while cell delay at FF is ~0.55-0.6x SS, so a path repaired to +10 at SS
# lands ~-30..-45 at FF: the band of every Qwen master.  Routes that kept WC,BC (S81) shared the SS IO model at FF.
#
# Session (active when OT_HOLD_MM=1 in the ORFS config; patched into load.tcl / util.tcl by tools/orfs_hold_mm.py):
#   scene WC = mode ss : the stage SDC exactly as ORFS / the recipe hooks maintain it (setup at SS; written back by
#                        write_sdc, so 6_final.sdc and sign-off see no change); its hold checks are DISABLED only while a
#                        repair runs (reset afterwards): SS hold is not a sign-off check and the shared-session IO hooks
#                        measure min arrivals over both scenes (fake WC hold).
#   scene BC = mode ff : refreshed from the ss SDC right before every repair, then the FF sign-off SDCs (OT_MM_FF_SDC:
#                        the job's sign-off post-SDCs / boundary file, read after set_propagated_clock as corner_sta reads
#                        them), setup disabled.  HOLD_SLACK_MARGIN therefore applies at FF only.
# repair_timing's -setup_margin guard sees the real SS setup when it places each FF hold cell (rev 3 hold-ECO "mm").
proc ot_mm_on {} { expr {[info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1"} }
proc ot_mm_libs {c} {
  # OWNER OPTION B (2026-10-07): the setup scene (named WC) reads the libraries of OT_MM_SETUP_CORNER (TC under option B)
  if {$c eq "WC" && [info exists ::env(OT_MM_SETUP_CORNER)] && $::env(OT_MM_SETUP_CORNER) ne ""} { set c $::env(OT_MM_SETUP_CORNER) }
  set k "[string toupper $c]_LIB_FILES"
  if {![info exists ::env($k)]} { error "OT_HOLD_MM: $k missing (route with --hold-corners WC,BC)" }
  return $::env($k)
}
proc ot_mm_sc {} { expr {[info exists ::env(OT_MM_SETUP_CORNER)] && $::env(OT_MM_SETUP_CORNER) ne "" ? $::env(OT_MM_SETUP_CORNER) : "WC"} }
proc ot_mm_read_libs {} {
  foreach c [list [ot_mm_sc] BC] { foreach l [ot_mm_libs $c] { log_cmd read_liberty $l } }
}
proc ot_mm_read_sdc {sdc} {
  log_cmd read_sdc -mode ss $sdc
  log_cmd read_sdc -mode ff $sdc
  define_scene [ot_mm_sc] -mode ss -liberty [ot_mm_libs [ot_mm_sc]]
  define_scene BC -mode ff -liberty [ot_mm_libs BC]
  # ff mode never checks setup; before CTS (ideal clocks) it checks nothing either, so placement repairs exactly as a
  # WC-only flow did.  Only the CTS (3_place.sdc) and global-route (4_cts.sdc) stages sync it before their repair.
  set_mode ff
  set_false_path -setup -from [all_clocks]
  set ::ot_mm_stage [file tail $sdc]
  if {$::ot_mm_stage ni {3_place.sdc 4_cts.sdc}} { set_false_path -hold -from [all_clocks] }
  set_mode ss
  set ::ot_mm_active 1
  puts "OT_HOLD_MM: scenes WC (mode ss) / BC (mode ff) from $sdc"
}
proc ot_mm_sync {} {
  if {![info exists ::ot_mm_active] || $::ot_mm_stage ni {3_place.sdc 4_cts.sdc}} { return }
  set f $::env(RESULTS_DIR)/ot_mm_ss_[clock clicks].sdc
  set_mode ss
  write_sdc -no_timestamp $f
  set_mode ff
  read_sdc $f
  file delete $f
  set_propagated_clock [all_clocks]
  if {[info exists ::env(OT_MM_FF_SDC)]} {
    foreach s $::env(OT_MM_FF_SDC) {
      if {![file exists $s]} { puts "OT_HOLD_MM WARNING: FF SDC $s missing: ff mode keeps the route SDC for it"; continue }
      puts "OT_HOLD_MM: ff mode reads $s"; read_sdc $s
    }
  }
  set_false_path -setup -from [all_clocks]
  set_mode ss
  set_false_path -hold -from [all_clocks]
  set ::ot_mm_synced 1
  # parasitics of the refreshed mode (the stage estimated them before calling the repair)
  estimate_parasitics [expr {$::ot_mm_stage eq "4_cts.sdc" ? "-global_routing" : "-placement"}]
  puts [format "OT_HOLD_MM sync: SS setup ws %.2f / FF hold ws %.2f ps" \
    [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
}
proc ot_mm_unsync {} {
  if {![info exists ::ot_mm_synced]} { return }
  set_mode ss
  unset_path_exceptions -hold -from [all_clocks]
  unset ::ot_mm_synced
  puts [format "OT_HOLD_MM after repair: SS setup ws %.2f / FF hold ws %.2f ps" \
    [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
}
proc ot_mm_ws {check scene} {
  set w 1e6
  foreach p [find_timing_paths -path_delay $check -scenes $scene -group_path_count 1] {
    set s [get_property $p slack]; if {$s ne "INF" && $s < $w} { set w $s }
  }
  return $w
}

# HOLD-STALL GUARD (unstick 2026-10-08).  repair_timing's hold repair has no progress limit: 138 loop jobs sat 4-25 h in
# CTS / GRT hold repair (it 10k-65k, ~2 buffers per iteration, WNS frozen for thousands of iterations; BF: 48k endpoints at
# -200 ps).  A window that wide is an RTL / constraint problem (missing pin register, wrong input-min / H1 SDC), not a
# buffering problem.  ot_repair_timing (called by the patched repair_timing_helper) keeps a setup-only or hold-only call
# unchanged; a combined call runs setup exactly as before, then hold in chunks of OT_HOLD_CHUNK iterations (default 1000)
# and stops when a chunk improves hold TNS by < OT_HOLD_MIN_GAIN_PCT % (default 2) and WNS by < 1 ps, when hold is
# already >= 0 and a chunk gains < 1 ps (chasing the margin only), or after OT_HOLD_MAX_HOURS (default 3) of hold repair.
# A stall with hold < 0 writes REPORTS_DIR/ot_hold_stall_<stage>.rpt (path classes, pin groups) and logs OT_HOLD_STALL:
# the closure loop reports it as NEEDS_RTL with that window instead of crawling.  OT_HOLD_GUARD=0 restores the old call.
proc ot_hold_guard_on {} { expr {![info exists ::env(OT_HOLD_GUARD)] || $::env(OT_HOLD_GUARD) ne "0"} }
proc ot_env_num {k d} { expr {[info exists ::env($k)] && [string is double -strict $::env($k)] ? $::env($k) : $d} }
proc ot_hold_paths {{limit 1000000}} {
  set sc {}
  if {[info exists ::ot_mm_synced]} { set sc [list -scenes BC] }
  return [find_timing_paths -path_delay min {*}$sc -group_path_count $limit -endpoint_path_count 1 -slack_max 0]
}
proc ot_hold_stats {} {
  # {worst hold slack, hold TNS, violating endpoints} in ps (FF scene in an mm session)
  set sc {}
  if {[info exists ::ot_mm_synced]} { set sc [list -scenes BC] }
  set w 1e6
  foreach p [find_timing_paths -path_delay min {*}$sc -group_path_count 1] {
    set s [get_property $p slack]; if {$s ne "INF" && $s < $w} { set w $s }
  }
  set tns 0.0; set n 0
  if {$w < 0} {
    foreach p [ot_hold_paths] { set s [get_property $p slack]; if {$s ne "INF" && $s < 0} { set tns [expr {$tns + $s}]; incr n } }
  }
  return [list $w $tns $n]
}
proc ot_pin_class {name} { expr {[string first "/" $name] < 0 ? "port" : "reg"} }
proc ot_hold_window_report {why hist} {
  set stage [expr {[info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/4_1_cts.odb] ? "grt" : "cts"}]
  set f [expr {[info exists ::env(REPORTS_DIR)] ? "$::env(REPORTS_DIR)/ot_hold_stall_${stage}.rpt" : "ot_hold_stall_${stage}.rpt"}]
  array set cls {}; array set cw {}; array set grp {}; array set gw {}; array set ex {}
  foreach p [ot_hold_paths 200000] {
    set s [get_property $p slack]; if {$s eq "INF"} { continue }
    set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]
    set c "[expr {[ot_pin_class $sp] eq "port" ? "I" : "R"}]2[expr {[ot_pin_class $ep] eq "port" ? "O" : "R"}]"
    incr cls($c); if {![info exists cw($c)] || $s < $cw($c)} { set cw($c) $s; set ex($c) "$sp -> $ep" }
    set g "$c [regsub -all {\[[0-9]+\]} $sp {[*]}] -> [regsub -all {\[[0-9]+\]} $ep {[*]}]"
    incr grp($g); if {![info exists gw($g)] || $s < $gw($g)} { set gw($g) $s }
  }
  set fh [open $f w]
  puts $fh "OT_HOLD_STALL NEEDS_RTL stage=$stage reason=$why"
  puts $fh "chunks (wns_ps tns_ps viol_endpoints): $hist"
  puts $fh "class  endpoints  worst_ps  worst_path   (I=input port, O=output port, R=register)"
  foreach c [lsort [array names cls]] { puts $fh [format "%-5s %10d %9.1f  %s" $c $cls($c) $cw($c) $ex($c)] }
  puts $fh "top pin groups (class start -> end, bus indices folded):"
  set rows {}
  foreach g [array names grp] { lappend rows [list $g $grp($g) $gw($g)] }
  foreach r [lrange [lsort -integer -decreasing -index 1 $rows] 0 29] { puts $fh [format "%7d %9.1f  %s" [lindex $r 1] [lindex $r 2] [lindex $r 0]] }
  close $fh
  set sum {}
  foreach c [lsort [array names cls]] { lappend sum "$c=$cls($c)@[format %.0f $cw($c)]" }
  puts "OT_HOLD_STALL NEEDS_RTL ($why): [join $sum { }] -> $f"
}
proc ot_repair_timing {rt_args} {
  if {![ot_hold_guard_on] || [lsearch -exact $rt_args -setup] >= 0 || [lsearch -exact $rt_args -hold] >= 0} {
    return [log_cmd repair_timing {*}$rt_args]
  }
  set hm 0.0
  set i [lsearch -exact $rt_args -hold_margin]; if {$i >= 0} { set hm [lindex $rt_args [expr {$i + 1}]] }
  set chunk [expr {int([ot_env_num OT_HOLD_CHUNK 1000])}]
  set mingain [ot_env_num OT_HOLD_MIN_GAIN_PCT 2.0]
  set maxs [expr {[ot_env_num OT_HOLD_MAX_HOURS 3.0] * 3600}]
  log_cmd repair_timing {*}$rt_args -setup
  if {[catch {set prev [ot_hold_stats]} msg]} {
    puts "OT_HOLD_GUARD: hold stats unavailable ($msg); unguarded hold repair"
    return [log_cmd repair_timing {*}$rt_args -hold]
  }
  set t0 [clock seconds]; set hist [list [lmap x $prev {format %.1f $x}]]
  puts "OT_HOLD_GUARD start: hold ws [format %.2f [lindex $prev 0]] tns [format %.1f [lindex $prev 1]] viol [lindex $prev 2] (margin $hm, chunk $chunk it)"
  for {set k 1} {1} {incr k} {
    if {[lindex $prev 0] >= $hm} { break }
    log_cmd repair_timing {*}$rt_args -hold -max_iterations $chunk
    set cur [ot_hold_stats]
    lappend hist [lmap x $cur {format %.1f $x}]
    lassign $prev w0 t0n n0; lassign $cur w1 t1n n1
    set dw [expr {$w1 - $w0}]
    set gain [expr {$t0n < 0 ? 100.0 * ($t1n - $t0n) / abs($t0n) : 0.0}]
    puts [format "OT_HOLD_GUARD chunk %d: hold ws %.2f (%+.2f) tns %.1f (%+.1f%%) viol %d, %d s" $k $w1 $dw $t1n $gain $n1 [expr {[clock seconds] - $t0}]]
    if {$w1 >= $hm} { break }
    if {$w1 >= 0 && $dw < 1.0} { puts "OT_HOLD_GUARD: hold met (ws [format %.2f $w1] >= 0); margin chase stalled, stop"; break }
    if {$dw < 1.0 && $gain < $mingain} { ot_hold_window_report "stalled: chunk $k gained [format %.2f $dw] ps / [format %.1f $gain]% TNS" $hist; break }
    if {[clock seconds] - $t0 > $maxs} { ot_hold_window_report "hold repair over [expr {$maxs / 3600.0}] h" $hist; break }
    set prev $cur
  }
}
