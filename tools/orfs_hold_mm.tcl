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
  # Scene creation clears the mode's external pin/wire loads and fanout.
  # Establish both scenes before evaluating the original SDC once per mode.
  set_mode ss
  set_mode ff
  define_scene [ot_mm_sc] -mode ss -liberty [ot_mm_libs [ot_mm_sc]]
  define_scene BC -mode ff -liberty [ot_mm_libs BC]
  log_cmd read_sdc -mode ss $sdc
  log_cmd read_sdc -mode ff $sdc
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
# MMFF-INSERTION 2026-10-08: the FF SDCs read into mode ff measure clock arrivals / latencies (io_ref_routed.sdc,
# vclk_corner_true.sdc, io_ref_skew.sdc, signoff/*.sdc ...).  In this TWO-scene STA `get_property <pin> arrival_*` is the
# extreme over BOTH scenes (arrival_max_rise = the WC TT/SS arrival: hbm_vm8_nws_s2_hm25 vclk 455.7 in the FF scene vs
# FF 380.2) and report_clock_latency may mix scenes.  While those SDCs are read: ::ot_ioref_scene = BC (io_ref_routed.sdc
# reads per-scene arrivals itself), get_property arrival_<max|min>_<rise|fall> of a pin is answered from scene BC
# (report_arrival -scene BC), and report_clock_latency without -scenes gets -scenes BC.  Restored right after.
proc ot_mm_arrival_bc {obj prop} {
  regexp {^arrival_(max|min)_(rise|fall)$} $prop -> mm rf
  sta::redirect_string_begin
  catch {report_arrival -scene BC -digits 4 $obj}
  set r [sta::redirect_string_end]
  set v ""; set k [string index $rf 0]
  foreach {- lo hi} [regexp -all -inline "\\s$k\\s+(\\S+):(\\S+)" $r] {
    set x [expr {$mm eq "max" ? $hi : $lo}]
    if {![string is double -strict $x]} continue
    if {$v eq "" || ($mm eq "max" ? $x > $v : $x < $v)} { set v $x }
  }
  return $v
}
proc ot_mm_scene_shim {on} {
  if {$on} {
    set ::ot_ioref_scene BC
    if {[llength [info commands ::ot_mm_orig_get_property]] || ![llength [info commands ::get_property]]} return
    if {![llength [info commands ::report_clock_latency]]} return
    rename ::get_property ::ot_mm_orig_get_property
    proc ::get_property {args} {
      set prop [lindex $args end]
      set ot_a $args
      if {[lindex $ot_a 0] eq "-object_type" && [lindex $ot_a 1] in {pin port}} { set ot_a [lrange $ot_a 2 end] }
      if {[regexp {^arrival_(max|min)_(rise|fall)$} $prop] && [llength $ot_a] == 2} {
        set o [lindex $ot_a 0]; set pl {}
        if {[string match {*_p_Pin} $o] || [string match {*_p_Port} $o]} { set pl [list $o] } elseif {[llength $o] == 1} {
          if {[catch {get_pins -quiet $o} pl] || [llength $pl] != 1} { if {[catch {get_ports -quiet $o} pl]} { set pl {} } }
        }
        if {[llength $pl] == 1} { return [ot_mm_arrival_bc [lindex $pl 0] $prop] }
      }
      return [uplevel 1 [list ::ot_mm_orig_get_property {*}$args]]
    }
    rename ::report_clock_latency ::ot_mm_orig_report_clock_latency
    proc ::report_clock_latency {args} {
      if {[lsearch -exact $args -scenes] < 0} { lappend args -scenes BC }
      return [uplevel 1 [list ::ot_mm_orig_report_clock_latency {*}$args]]
    }
  } else {
    catch {unset ::ot_ioref_scene}
    if {![llength [info commands ::ot_mm_orig_get_property]]} return
    rename ::get_property {}; rename ::ot_mm_orig_get_property ::get_property
    rename ::report_clock_latency {}; rename ::ot_mm_orig_report_clock_latency ::report_clock_latency
  }
}
# FF sign-off SDCs can recreate a real root at the sign-off period after the
# copied route SDC created its link-budget virtual clock at the route period.
# These virtual clocks represent that exact root, so keep their periods equal.
# Recreating the existing clock updates its waveform in place; IO constraints,
# latency and uncertainty remain attached. Other virtual/window clocks stay put.
proc ot_mm_sync_link_periods {} {
  if {[llength [info commands ot_single_clock_check]]} { ot_single_clock_check }
  foreach c [all_clocks] {
    set vn [get_full_name $c]
    if {![regexp {^ot_lb_v_(.+)$} $vn -> rn] || [llength [get_property $c sources]]} continue
    set rc [get_clocks -quiet $rn]
    if {[llength $rc] != 1 || ![llength [get_property $rc sources]]} continue
    set vt [get_property $c period]
    set rt [get_property $rc period]
    if {abs($vt - $rt) > 0.000001} {
      set wave [lmap edge [$c waveform] {expr {$edge / [$c period] * $rt}}]
      create_clock -name $vn -period $rt -waveform $wave
      puts "OT_HOLD_MM virtual period: $vn $vt -> $rt (reference $rn)"
    }
  }
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
  # MMFF-PARASITICS (el1011-q-kvd 2026-10-12): the FF SDCs below MEASURE BC clock arrivals (QDM reference pin, io_ref
  # pin flops) and turn them into the input-min / output-min delays.  Until now the BC scene was estimated only at the
  # END of this proc, so a tree built in the stage (clock spine, CTS) was measured WITHOUT wire parasitics:
  # qkd_d2d_ref (ot_qkvd_kv_end, 1.56 ns TT spine) read BC 745.7 ps at the reference flop, the estimated BC tree is
  # 1,180-1,242 ps, and 2,143 input pins got a 500 ps fake hold hole (FF hold -501.9, flat over 2,000 repair
  # iterations: EARLY_FAIL_HOLD).  Estimate first so the reference and the hold check see the same tree.
  estimate_parasitics [expr {$::ot_mm_stage eq "4_cts.sdc" ? "-global_routing" : "-placement"}]
  set ot_mm_ioref_read 0
  ot_mm_scene_shim 1
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
  ot_mm_sync_link_periods
  ot_mm_scene_shim 0
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

# RC-CAL (ROOT-RST 2026-10-19, s81lk_kp4_dec-p1-e86bf8cae): route-time HOLD repair times the clock trees on the
# RCX-calibrated upper-layer RC, not on the platform setRC.tcl values.  setRC.tcl (asap7) prices M6 / M7 wire at
# 0.187 / 0.163 fF/um; OpenRCX extracts an isolated clock trunk on those layers at 0.096-0.108 fF/um and 13.1-14.9
# ohm/um (kp4_dec BUFx24 spine trunks N147_r1 / N73_r1 / N73_r2 / N73 / N36, smhq spine M6 / M7 medians).  The spine's
# wire-dominated BUFx24 trunk was therefore estimated ~90 ps LATE at GRT-FF (pin flops p_d__ot_q median 506.8 GRT vs
# 415.0 routed) while the cell-dominated pad chain to the hard child u_syn tracked (299.9 vs 275.4): the GRT hold repair
# saw +30 on parent pin flop -> u_syn/p_d paths that signed off at -64.76.  Measured on the same 5_1_grt.odb with these
# values: p_d__ot_q 440.0 / u_syn 286.7 (pair error 67 -> 14 ps); a TritonCTS block (hcoll_kqs_leaf, no M6 / M7
# clock) is unchanged.  Scope: ONLY the hold part of repair_timing_helper (setup repair, GRT, and every other stage keep
# the platform RC; restored right after).  GRT stage (global routes present): set_layer_rc M6 / M7.  CTS stage (placement
# parasitics): set_wire_rc -clock, and only when a clock spine was built in this session (a TritonCTS tree's low-layer
# clock wiring is NOT over-estimated: the clock-wide value moved hcoll -16 ps the wrong way).  Data wires on M6 / M7
# also get the lower C, which only makes them faster under a min-delay check (conservative for hold).
# Knobs: OT_RC_CAL=0 off; OT_RC_CAL_R / OT_RC_CAL_C in setRC.tcl units (defaults 1.40E-02 = 14 ohm/um, 1.05E-01 fF/um),
# OT_RC_CAL_LAYERS (default "M6 M7").  asap7 only.  The spine balancing (clock_spine.tcl) uses the same procs.
proc ot_rc_cal_on {} {
  expr {(![info exists ::env(OT_RC_CAL)] || $::env(OT_RC_CAL) ne "0") &&
        [info exists ::env(PLATFORM)] && $::env(PLATFORM) eq "asap7"}
}
proc ot_rc_cal_rc {} {
  set r [expr {[info exists ::env(OT_RC_CAL_R)] && [string is double -strict $::env(OT_RC_CAL_R)] ? $::env(OT_RC_CAL_R) : 1.40E-02}]
  set c [expr {[info exists ::env(OT_RC_CAL_C)] && [string is double -strict $::env(OT_RC_CAL_C)] ? $::env(OT_RC_CAL_C) : 1.05E-01}]
  return [list $r $c]
}
proc ot_rc_cal_mode {} {
  # the parasitics the stage estimates: global routes present -> -global_routing, else -placement
  if {![catch {grt::have_routes} h] && $h} { return "-global_routing" }
  return "-placement"
}
proc ot_rc_cal_spine {} {
  expr {([info exists ::ot_sp_all_insts] && [llength $::ot_sp_all_insts]) ||
        ([info exists ::ot_sp_insts] && [llength $::ot_sp_insts])}
}
# set the calibrated RC for KIND (hold | spine); returns 1 when anything was changed (the caller re-estimates and later
# calls ot_rc_cal_restore)
proc ot_rc_cal_apply {kind} {
  if {![ot_rc_cal_on]} { return 0 }
  lassign [ot_rc_cal_rc] r c
  set mode [ot_rc_cal_mode]
  if {$mode eq "-global_routing"} {
    set ls [expr {[info exists ::env(OT_RC_CAL_LAYERS)] ? $::env(OT_RC_CAL_LAYERS) : "M6 M7"}]
    foreach l $ls { set_layer_rc -layer $l -resistance $r -capacitance $c }
    puts "OT_RC_CAL $kind: $mode layers $ls R $r C $c (RCX-calibrated upper-layer RC; platform setRC restored after)"
    return 1
  }
  if {$kind ne "spine" && ![ot_rc_cal_spine]} { return 0 }
  set_wire_rc -clock -resistance $r -capacitance $c
  puts "OT_RC_CAL $kind: $mode clock wire R $r C $c (spine clock; platform setRC restored after)"
  return 1
}
proc ot_rc_cal_restore {} {
  source $::env(PLATFORM_DIR)/setRC.tcl
  puts "OT_RC_CAL restored platform setRC.tcl"
}
# Run BODY with calibrated hold RC. Numeric FF I/O references must be measured
# with that same RC, and measured again after restoring platform RC. Unsync FIRST:
# writing the SS SDC while its temporary hold exception is active would copy that
# exception to FF and hide real hold paths. Never refresh a scene that was not
# already synced by the caller; non-MM and setup-only behavior stays unchanged.
proc ot_rc_cal_hold {body} {
  set on [ot_rc_cal_apply hold]
  set refresh [expr {$on && [info exists ::ot_mm_synced]}]
  try {
    if {$on} {
      estimate_parasitics [ot_rc_cal_mode]
      if {$refresh} { ot_mm_unsync; ot_mm_sync }
    }
    return [uplevel 1 $body]
  } finally {
    if {$on} {
      ot_rc_cal_restore
      estimate_parasitics [ot_rc_cal_mode]
      if {$refresh} { ot_mm_unsync; ot_mm_sync }
    }
  }
}

# HOLD-STALL GUARD (unstick 2026-10-08).  repair_timing's hold repair has no progress limit: 138 loop jobs sat 4-25 h in
# CTS / GRT hold repair (it 10k-65k, ~2 buffers per iteration, WNS frozen for thousands of iterations; BF: 48k endpoints at
# -200 ps).  A window that wide is an RTL / constraint problem (missing pin register, wrong input-min / H1 SDC), not a
# buffering problem.  ot_repair_timing (called by the patched repair_timing_helper) keeps a setup-only or hold-only call
# unchanged; a combined call runs setup exactly as before, then hold in chunks of OT_HOLD_CHUNK iterations (default 1000)
# and stops when a chunk improves hold TNS by < OT_HOLD_MIN_GAIN_PCT % (default 2) and WNS by < 1 ps, when hold is
# already >= 0 and a chunk gains < 1 ps (chasing the margin only), or after OT_HOLD_MAX_HOURS (default 3) of hold repair.
# After an HM-AUTO flood reduction the hold repair first runs at HM 0 and stops once real hold is met (MET-FIRST below).
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
# HOLD-STOP (drive-resume 2026-10-09, coordinator APPROVED).  A hold repair that stalls already within a small margin
# (stuckscan: real FF hold WNS >= -15 ps, setup not hopeless) is NOT early-failed: the route continues and the
# post-route hold ECO repairs the residue.  repair_timing cannot be interrupted, so the closure loop stops the stage and
# resumes it from its checkpoint with OT_HOLD_STOP = "<stage>:<buffers> ..." (stage cts | grt).  For that stage the hold
# repair runs once with -max_buffer_percent set to <buffers> over the instance count -- the stalled run's buffer count
# when it reached its final WNS, so the converging part replays and the flat tail is cut -- and <buffers> = 0 skips the
# hold repair.  Setup repair is unchanged.  The cap ends the call with RSZ-0060; the stage continues on the repaired
# design ("OT_HOLD_MM after repair" lets tolerate_flow_errors zero that one error).
proc ot_hold_stage {} {
  expr {[info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/4_1_cts.odb] ? "grt" : "cts"}
}
proc ot_hold_stop_cap {stage} {
  # -> "" (no stop for this stage) or the buffer cap (0 = skip the hold repair)
  if {![info exists ::env(OT_HOLD_STOP)]} { return "" }
  foreach e [split $::env(OT_HOLD_STOP) " ,;"] {
    if {[regexp {^(cts|grt):([0-9]+)$} $e -> s n] && $s eq $stage} { return $n }
  }
  return ""
}
proc ot_hold_stop_args {rt_args pct} {
  set i [lsearch -exact $rt_args -max_buffer_percent]
  if {$i >= 0} { return [lreplace $rt_args [expr {$i + 1}] [expr {$i + 1}] $pct] }
  return [concat $rt_args [list -max_buffer_percent $pct]]
}
proc ot_hold_stop {rt_args} {
  # 1 when OT_HOLD_STOP handled this stage's hold repair (skipped or capped), else 0
  set stage [ot_hold_stage]
  set n [ot_hold_stop_cap $stage]
  if {$n eq ""} { return 0 }
  if {$n == 0} {
    puts "OT_HOLD_STOP stage=$stage: hold repair skipped (near-miss stall; the post-route hold ECO repairs the residue)"
    return 1
  }
  set inst 0
  catch { set inst [llength [[ord::get_db_block] getInsts]] }
  if {$inst <= 0} { puts "OT_HOLD_STOP stage=$stage: instance count unavailable; hold repair skipped"; return 1 }
  set pct [format %.6f [expr {100.0 * $n / $inst}]]
  puts "OT_HOLD_STOP stage=$stage: hold repair capped at $n buffers (-max_buffer_percent $pct of $inst instances)"
  if {[catch {log_cmd repair_timing {*}[ot_hold_stop_args $rt_args $pct] -hold} err]} {
    if {![regexp {RSZ-0060|Max buffer count} $err]} { error $err }
    puts "OT_HOLD_MM after repair: OT_HOLD_STOP cap of $n buffers reached (RSZ-0060); continuing to route"
  }
  catch { lassign [ot_hold_stats] w t v; puts [format "OT_HOLD_STOP stage=%s done: hold ws %.2f tns %.1f viol %d" $stage $w $t $v] }
  return 1
}
# Owner 2026-10-25: structural FF hold failures must stop BEFORE repair_timing. Its
# -max_iterations bounds inner passes, not the endpoint sweep, so the stall guard
# cannot interrupt a single call that adds hundreds of thousands of buffers.
# Count true negative-slack endpoints (ot_hold_stats), never the repair margin.
proc ot_hold_structural_gate {} {
  # ot_mm_sync creates/times the real FF BC scene with its own FF boundary SDC.
  # A primary-corner min path is not evidence of FF hold: fail closed without it.
  if {![info exists ::ot_mm_active] || !$::ot_mm_active ||
      ![info exists ::ot_mm_synced] || !$::ot_mm_synced} {
    return -code error -errorcode {OPENTALLAS HOLD_FF_UNAVAILABLE} "OT_HOLD_STRUCTURAL: synchronized FF scene BC unavailable; enable multi-mode FF timing before hold repair"
  }
  lassign [ot_hold_stats] w t n
  if {$w >= -100.0 && $n <= 2000} { return }
  set stage [ot_hold_stage]
  set msg [format "OT_HOLD_STRUCTURAL stage=%s: FF hold ws %.2f ps, %d true failing endpoints (limits: ws >= -100 ps, endpoints <= 2000); revise plan/RTL/boundary before repair" $stage $w $n]
  puts $msg
  catch {
    set f [expr {[info exists ::env(REPORTS_DIR)] ? "$::env(REPORTS_DIR)/ot_hold_structural_${stage}.rpt" : "ot_hold_structural_${stage}.rpt"}]
    set fh [open $f w]; puts $fh $msg; close $fh
  }
  return -code error -errorcode {OPENTALLAS HOLD_STRUCTURAL} $msg
}
proc ot_repair_timing {rt_args} {
  set setup [expr {[lsearch -exact $rt_args -setup] >= 0}]
  set hold [expr {[lsearch -exact $rt_args -hold] >= 0}]
  if {$setup && !$hold} { return [log_cmd repair_timing {*}$rt_args] }
  if {$hold && !$setup} {
    return [ot_rc_cal_hold {
      ot_hold_structural_gate
      log_cmd repair_timing {*}[ot_hm_guard $rt_args]
    }]
  }
  # Explicit -setup -hold and the no-flag form both request combined repair.
  # Keep setup on normal RC, then gate/repair hold on calibrated FF clock RC.
  set args {}
  foreach arg $rt_args { if {$arg ni {-setup -hold}} { lappend args $arg } }
  set rt_args $args
  log_cmd repair_timing {*}$rt_args -setup
  if {![ot_hold_guard_on]} {
    return [ot_rc_cal_hold {
      ot_hold_structural_gate
      log_cmd repair_timing {*}[ot_hm_guard $rt_args] -hold
    }]
  }
  return [ot_rc_cal_hold { ot_repair_hold_guarded $rt_args }]
}
proc ot_repair_hold_guarded {rt_args} {
  set hm 0.0
  set i [lsearch -exact $rt_args -hold_margin]; if {$i >= 0} { set hm [lindex $rt_args [expr {$i + 1}]] }
  set chunk [expr {int([ot_env_num OT_HOLD_CHUNK 1000])}]
  set mingain [ot_env_num OT_HOLD_MIN_GAIN_PCT 2.0]
  set maxs [expr {[ot_env_num OT_HOLD_MAX_HOURS 3.0] * 3600}]
  ot_hold_structural_gate
  set hm_asked $hm
  set rt_args [ot_hm_guard $rt_args]
  if {[ot_hold_stop $rt_args]} { return }
  set i [lsearch -exact $rt_args -hold_margin]; if {$i >= 0} { set hm [lindex $rt_args [expr {$i + 1}]] }
  if {[catch {set prev [ot_hold_stats]} msg]} {
    puts "OT_HOLD_GUARD: hold stats unavailable ($msg); unguarded hold repair"
    return [log_cmd repair_timing {*}$rt_args -hold]
  }
  # MET-FIRST on a margin flood (drive-2155 2026-10-08, OWNER: the hold margin is a design target, HM 0 allowed; a route
  # whose real FF hold is met stops repairing).  repair_timing's hold pass visits EVERY endpoint inside the margin in one
  # call (-max_iterations does not bound it), so after an HM-AUTO flood reduction (worst + floor) the call still pads all
  # of them: hbm_su_ctlh vf-lvt met real hold at 7.7k buffers, then spent 2.3 h / 58k more buffers on 60k endpoints for
  # +4.4 ps.  When the guard flagged a flood, repair at HM 0 (real violations only) and stop once met.  Disable with
  # OT_HOLD_FLOOD_MET_FIRST=0.
  if {$hm < $hm_asked && [ot_env_num OT_HOLD_FLOOD_MET_FIRST 1] != 0 && $i >= 0} {
    if {[lindex $prev 0] < 0} {
      puts "OT_HOLD_GUARD start: hold ws [format %.2f [lindex $prev 0]] tns [format %.1f [lindex $prev 1]] viol [lindex $prev 2] (met-first at HM 0 after a margin flood; asked $hm_asked, auto $hm)"
      log_cmd repair_timing {*}[lreplace $rt_args [expr {$i + 1}] [expr {$i + 1}] 0.0] -hold
      set prev [ot_hold_stats]
    }
    if {[lindex $prev 0] >= 0} {
      puts [format "OT_HOLD_GUARD: hold met (ws %.2f >= 0) at HM 0 after a margin flood (asked %g, auto %g); margin chase skipped, stop" [lindex $prev 0] $hm_asked $hm]
      return
    }
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

# MACRO-CLK (2026-10-10): this helper is sourced in every ORFS stage of every run_abi3_physical / hbm_accel_smh route, so
# it carries the flow-default macro clock clustering (clock_tree_synthesis wrapper; physical/common_flow/
# macro_cts_cluster.tcl, which the closure loop ships into older snapshots next to this file).
if {[info commands ot_mcc_cts_orig] eq ""} {
  set ot_mcc_file [file join [file dirname [file dirname [file normalize [info script]]]] physical common_flow macro_cts_cluster.tcl]
  if {[file exists $ot_mcc_file]} { source $ot_mcc_file } else { puts "OT_MACRO_CTS unavailable: $ot_mcc_file missing" }
}
