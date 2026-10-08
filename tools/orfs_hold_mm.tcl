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
