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
  set ot_mm_ioref_read 0
  if {[info exists ::env(OT_MM_FF_SDC)]} {
    foreach s $::env(OT_MM_FF_SDC) {
      if {![file exists $s]} { puts "OT_HOLD_MM WARNING: FF SDC $s missing: ff mode keeps the route SDC for it"; continue }
      if {[file tail $s] eq "io_ref_routed.sdc"} { set ot_mm_ioref_read 1 }
      puts "OT_HOLD_MM: ff mode reads $s"; read_sdc $s
    }
  }
  # MMFF-IOREF 2026-10-08: the closure loop drops {SRC}/.ot_mm/ff_ioref_last.sdc (a copy of io_ref_routed.sdc; absent
  # when the spec opts out with route_ff_ioref: false).  It is read LAST, whatever OT_MM_FF_SDC the route command itself
  # exported: an inline `export OT_MM_FF_SDC=...` in a job's route cmd overrode the loop's appended io_ref_routed.sdc,
  # so the FF scene timed vclk at the assumed insertion (hbm_quant_ts0spl_tt: vclk FF 373 vs measured 546 -> fake
  # 4_1_cts hold -334 on 32k endpoints).  Skipped when the list already read an io_ref_routed.sdc.
  set ot_mm_ioref_file [expr {[info exists ::env(OT_MM_IOREF_FILE)] ? $::env(OT_MM_IOREF_FILE) : "/src/.ot_mm/ff_ioref_last.sdc"}]
  if {!$ot_mm_ioref_read && [file exists $ot_mm_ioref_file]} {
    puts "OT_HOLD_MM: ff mode reads $ot_mm_ioref_file (loop default, appended last)"; read_sdc $ot_mm_ioref_file
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
# HM-GUARD (hm-guard 2026-10-08).  HM 50 is a design margin, acceptance is FF hold >= 0 (post-route hold ECO as before).
# A block whose REAL FF hold already passes can still have tens of thousands of back-to-back flop pairs inside the 50 ps
# margin; repair_timing pads every one: S81 PQ root CAM 17.2k endpoints -> 21.7k buffers (85.8 -> 95.7%), HBM VM8 ~102k
# buffers, Qwen link rx128 72.5k endpoints -> 146k buffers (80.7 -> 97.2%, 6h53m) -- all DPL-0033.  Before a hold repair
# ot_hm_guard counts the FF endpoints inside the margin and projects the buffer area (ceil(deficit / OT_HM_BUF_PS) buffers
# of OT_HM_BUF_AREA_UM2 each over the core area).  Over OT_HM_GUARD_MAX_EP endpoints (10k) or OT_HM_GUARD_MAX_UTIL_PTS
# (8 points) the margin of THIS run drops to max(floor, worst real violation + floor), floor OT_HM_GUARD_FLOOR_PS (10),
# never above the asked margin; it logs "OT_HM_AUTO" and writes REPORTS_DIR/ot_hm_auto_<stage>.rpt (the closure loop
# turns it into a job event).  OT_HM_GUARD=0 disables it.  Margins in the library unit (ps on asap7).
proc ot_hm_buffers {slacks hm buf_ps} {
  # projected hold buffers: one per buf_ps of deficit below the margin, per endpoint
  set n 0
  foreach s $slacks { if {$s < $hm} { incr n [expr {int(ceil(($hm - $s) / double($buf_ps)))}] } }
  return $n
}
proc ot_hm_decide {hm worst n_in buffers core_um2 buf_area max_ep max_pts floor} {
  # -> {new_margin util_pts reason}; new_margin == hm when no reduction
  set pts [expr {$core_um2 > 0 ? 100.0 * $buffers * $buf_area / $core_um2 : 0.0}]
  if {$hm <= $floor} { return [list $hm $pts "margin $hm <= floor $floor"] }
  set why {}
  if {$n_in > $max_ep} { lappend why "$n_in endpoints in margin > $max_ep" }
  if {$pts > $max_pts} { lappend why [format "projected +%.1f util points > %g" $pts $max_pts] }
  if {![llength $why]} { return [list $hm $pts "within limits"] }
  set viol [expr {$worst < 0 ? -$worst : 0.0}]
  set new [expr {max($floor, $viol + $floor)}]
  set new [expr {min($hm, ceil($new * 10.0) / 10.0)}]
  return [list $new $pts [join $why "; "]]
}
proc ot_hm_core_um2 {} {
  if {[catch {
    set blk [ord::get_db_block]; set r [$blk getCoreArea]
    set u [$blk getDbUnitsPerMicron]
    set a [expr {double([$r dx]) * [$r dy] / ($u * $u)}]
  }]} { return 0.0 }
  return $a
}
proc ot_hm_guard {rt_args} {
  if {[info exists ::env(OT_HM_GUARD)] && $::env(OT_HM_GUARD) eq "0"} { return $rt_args }
  set i [lsearch -exact $rt_args -hold_margin]; if {$i < 0} { return $rt_args }
  set hm [lindex $rt_args [expr {$i + 1}]]
  set floor [ot_env_num OT_HM_GUARD_FLOOR_PS 10.0]
  if {![string is double -strict $hm] || $hm <= $floor} { return $rt_args }
  if {[catch {
    set sc {}; if {[info exists ::ot_mm_synced]} { set sc [list -scenes BC] }
    set slacks {}; set worst 1e6
    foreach p [find_timing_paths -path_delay min {*}$sc -group_path_count 1000000 -endpoint_path_count 1 -slack_max $hm] {
      set s [get_property $p slack]; if {$s eq "INF"} { continue }
      lappend slacks $s; if {$s < $worst} { set worst $s }
    }
    if {![llength $slacks]} { set worst [lindex [ot_hold_stats] 0] }
  } msg]} { puts "OT_HM_GUARD: endpoint count unavailable ($msg); margin $hm kept"; return $rt_args }
  set n [llength $slacks]
  set buf_area [ot_env_num OT_HM_BUF_AREA_UM2 0.08]
  set nb [ot_hm_buffers $slacks $hm [ot_env_num OT_HM_BUF_PS 20.0]]
  set core [ot_hm_core_um2]
  lassign [ot_hm_decide $hm $worst $n $nb $core $buf_area [ot_env_num OT_HM_GUARD_MAX_EP 10000] \
             [ot_env_num OT_HM_GUARD_MAX_UTIL_PTS 8.0] $floor] new pts why
  set line [format "HM auto-reduced %g->%g: %d endpoints in margin (worst FF hold %.2f, ~%d buffers, +%.1f util pts of %.0f um2 core; %s)" \
    $hm $new $n $worst $nb $pts $core $why]
  if {$new >= $hm} {
    puts [format "OT_HM_GUARD: margin %g kept: %d endpoints in margin, ~%d buffers, +%.1f util pts (%s)" $hm $n $nb $pts $why]
    return $rt_args
  }
  puts "OT_HM_AUTO $line"
  set stage [expr {[info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/4_1_cts.odb] ? "grt" : "cts"}]
  catch {
    set f [expr {[info exists ::env(REPORTS_DIR)] ? "$::env(REPORTS_DIR)/ot_hm_auto_${stage}.rpt" : "ot_hm_auto_${stage}.rpt"}]
    set fh [open $f w]; puts $fh "OT_HM_AUTO stage=$stage $line"; close $fh
  }
  return [lreplace $rt_args [expr {$i + 1}] [expr {$i + 1}] $new]
}
proc ot_repair_timing {rt_args} {
  if {![ot_hold_guard_on] || [lsearch -exact $rt_args -setup] >= 0 || [lsearch -exact $rt_args -hold] >= 0} {
    if {[lsearch -exact $rt_args -setup] < 0} { set rt_args [ot_hm_guard $rt_args] }
    return [log_cmd repair_timing {*}$rt_args]
  }
  set hm 0.0
  set i [lsearch -exact $rt_args -hold_margin]; if {$i >= 0} { set hm [lindex $rt_args [expr {$i + 1}]] }
  set chunk [expr {int([ot_env_num OT_HOLD_CHUNK 1000])}]
  set mingain [ot_env_num OT_HOLD_MIN_GAIN_PCT 2.0]
  set maxs [expr {[ot_env_num OT_HOLD_MAX_HOURS 3.0] * 3600}]
  log_cmd repair_timing {*}$rt_args -setup
  set rt_args [ot_hm_guard $rt_args]
  set i [lsearch -exact $rt_args -hold_margin]; if {$i >= 0} { set hm [lindex $rt_args [expr {$i + 1}]] }
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
