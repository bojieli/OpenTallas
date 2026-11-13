# FF-only post-CTS structural hold gate, before any hold repair (owner 2026-10-25 00:46).
if {![info exists ::env(PLIBS)] || ![llength $::env(PLIBS)]} { error "hold gate: BC_LIB_FILES missing" }
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
# FLOW 10-25: the FF gate times the IO paths against the FF-bound vclk (ruling 9.7 / 5e) on the kit's RC basis
if {[info exists ::env(OT_VCLK_FF)] && $::env(OT_VCLK_FF) ne ""} {
  source [file join [file dirname [file normalize [info script]]] vclk_corner.tcl]
  ot_vclk_bind ff
}
if {[info exists ::env(LAYER_PARASITICS_FILE)] && $::env(LAYER_PARASITICS_FILE) ne ""} {
  source $::env(LAYER_PARASITICS_FILE)
} else {
  source $::env(PLATFORM_DIR)/setRC.tcl
}
estimate_parasitics -placement
# Match signoff.py's fixed boundary contract; uncertainty is already in the SDC.
set vclks {}; set clock_ports {}
foreach c [all_clocks] {
  set src [get_property $c sources]
  if {![llength $src]} { lappend vclks $c }
  foreach s $src { lappend clock_ports [get_full_name $s] }
}
if {[llength $vclks] != 1} { error "hold gate: expected one IO virtual clock" }
# FLOW-16 10-31 (same scope as signoff._fwd_ring_tcl, COORD 10-29 21:11 (3)): source-synchronous landing-ring inputs
# (golden SDC tag # OT_FWD_RING_INPUTS <fclk> <ports>) stay timed against their forwarded write clock. The vclk overlay
# below would replace their forwarded-clock input delays (OpenSTA drops the other-clock delays of a port), which hid
# every ring-write hold path from this gate (HEAD l47 hd_turn_a: gate -57/2 vs kit SDC -185/2274, GRT RSZ-0060).
set hg_fwd {}; set hg_fwd_ports {}; set hg_ring_in ""
set hg_native {}; set hg_native_ports {}
set hg_gold [file join [file dirname [file normalize [info script]]] constraint.sdc]
if {[info exists ::env(OT_GOLDEN_SDC)] && $::env(OT_GOLDEN_SDC) ne ""} { set hg_gold $::env(OT_GOLDEN_SDC) }
if {[file exists $hg_gold]} {
  set f [open $hg_gold]; set hg_txt [read $f]; close $f
  foreach line [split $hg_txt "\n"] {
    # S81-RINGHOLD-3 opt-in plan clock.ring_hold: the measured sender data-vs-fclk min replaces the seam fallback
    if {[regexp {^# OT_FWD_RING_MIN (\S+)$} $line -> hg_ring_in]} continue
    if {[string match {# OT_NATIVE_PAD_INPUT*} $line]} {
      set w [regexp -all -inline {\S+} $line]
      if {[llength $w] != 6 || [lindex $w 1] ne "OT_NATIVE_PAD_INPUT"} {error "hold gate: malformed OT_NATIVE_PAD_INPUT: $line"}
      lassign [lrange $w 2 end] ck sel mn mx
      if {![regexp {^[A-Za-z_][A-Za-z0-9_]*$} $ck] || ![regexp {^[A-Za-z_][A-Za-z0-9_]*\[\*\]$} $sel]
          || ![string is double -strict $mn] || ![string is double -strict $mx]
          || [regexp -nocase {inf|nan} "$mn $mx"] || $mn > $mx} {error "hold gate: invalid native pad contract: $line"}
      if {[llength [get_clocks -quiet $ck]] != 1} {error "hold gate: missing native pad clock $ck"}
      set ps [get_ports -quiet $sel]
      if {![llength $ps]} {error "hold gate: empty native pad selector $sel"}
      foreach q $ps {
        set pn [get_full_name $q]
        if {$pn in $hg_native_ports || $pn in $clock_ports || $q ni [all_inputs]} {error "hold gate: ambiguous native pad input $pn"}
        lappend hg_native_ports $pn
      }
      lappend hg_native [list $ck $sel $mn $mx]
      continue
    }
    if {![string match {# OT_FWD_RING_INPUTS *} $line]} continue
    set w [regexp -all -inline {\S+} $line]
    if {[llength $w] < 4} { error "hold gate: malformed OT_FWD_RING_INPUTS line: $line" }
    lappend hg_fwd [list [lindex $w 2] [lrange $w 3 end]]
    foreach s [lrange $w 3 end] { foreach q [get_ports $s] { lappend hg_fwd_ports [get_full_name $q] } }
  }
}
set din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $clock_ports && [get_full_name $p] ni $hg_fwd_ports && [get_full_name $p] ni $hg_native_ports} { lappend din $p } }
# CLOCK-RESET IO-HOLD 10-25: the kit's seam hold contract (gen_phys.seam_hold via config.mk); legacy -40 / 0
set hg_in -40; set hg_out 0
if {[info exists ::env(OT_HOLD_IN_MIN)] && $::env(OT_HOLD_IN_MIN) ne ""} { set hg_in $::env(OT_HOLD_IN_MIN) }
if {[info exists ::env(OT_HOLD_OUT_MIN)] && $::env(OT_HOLD_OUT_MIN) ne ""} { set hg_out $::env(OT_HOLD_OUT_MIN) }
# plan clock.tap_window (gen_phys.tap_window_ps): the SDC min output delay is the contract + W (the clock ports are
# timed W early), so the waiver guard applies to the contract part
set hg_win 0
if {[info exists ::env(OT_TAP_WINDOW)] && $::env(OT_TAP_WINDOW) ne ""} { set hg_win $::env(OT_TAP_WINDOW) }
if {$hg_out - $hg_win > 0} { error "hold gate: min output delay $hg_out - window $hg_win > 0 waives the sender hold check" }
puts "OT_HOLD_GATE contract in_min $hg_in out_min $hg_out"
if {[llength $din]} { set_input_delay -min $hg_in -clock [lindex $vclks 0] $din }
# IO-HOLD option A (opt-in, gen_phys.io_hold_tcl): partition-driven inputs carry their sender's guaranteed output-min
set ioh [file join [file dirname [file normalize [info script]]] io_hold.tcl]
if {[file exists $ioh]} { source $ioh; ot_io_hold_apply [lindex $vclks 0] }
if {[llength [all_outputs]]} { set_output_delay -min $hg_out -clock [lindex $vclks 0] [all_outputs] }
# the ring inputs get the same overlay min on their own forwarded clock (signoff._fwd_ring_tcl), after io_hold.tcl
if {$hg_ring_in eq ""} { set hg_ring_in $hg_in }
foreach r $hg_fwd { lassign $r ck sels; foreach s $sels { set_input_delay -min $hg_ring_in -clock [get_clocks $ck] [get_ports $s] } }
if {[llength $hg_fwd]} { puts "OT_HOLD_GATE forwarded ring inputs [llength $hg_fwd_ports] on [llength $hg_fwd] clock(s), min $hg_ring_in" }
# Restore the golden native eye exactly after all generic/per-port overlays. No seam budget applies here.
foreach r $hg_native {
  lassign $r ck sel mn mx
  set_input_delay -min $mn -clock [get_clocks $ck] [get_ports $sel]
  set_input_delay -max $mx -clock [get_clocks $ck] [get_ports $sel]
}
if {[llength $hg_native]} {puts "OT_HOLD_GATE native pad inputs [llength $hg_native_ports], golden delays preserved"}
# A separate FF-only process: do not impersonate the shared multi-mode context.
# Owner thresholds match orfs_hold_mm.tcl, applied to actual negative endpoints.
set w [sta::time_sta_ui [sta::worst_slack_cmd min]]
set n [sta::endpoint_violation_count min]
if {![string is double -strict $w] || ![string is integer -strict $n]} {
  error "hold gate: true FF hold statistics unavailable"
}
# COORD 18:0x (3) (A), FLOW-19 10-31: the -100 structural limit was set on the legacy -40 seam contract; a deeper plan
# seam contract (clock.seam_hold seam_ps, HEAD l48w in_min -90) moves every zero-logic input endpoint by the same
# amount, so the limit counts from the kit's contract: lim = -100 + min(0, in_min + 40) (-150 at -90, -100 at -40 or
# shallower: never stricter).  in_min = OT_HOLD_IN_MIN (config.mk), else the kit SDC's vclk min input delay on the
# non-clock inputs, else the legacy -40.  Endpoint cap 2000 unchanged.
set hg_cin $hg_in
if {![info exists ::env(OT_HOLD_IN_MIN)] || $::env(OT_HOLD_IN_MIN) eq ""} {
  if {[info exists hg_txt] && [regexp {set_input_delay\s+-min\s+(-?[0-9.]+)\s+-clock\s+\S+\s+\$non_clk_in} $hg_txt -> v]} {
    set hg_cin $v
  }
}
# COORD 22:02 (DIE-HEAD-53 ASK): the per-type tap window W_t (OT_TAP_WINDOW, the SDC's -source -early -W_t on the tap
# ports) shifts every cross-tap flop pair's hold exactly as in_min shifts the input hold: lim = -100 + min(0,
# in_min + 40, -W_t).  The 2000-endpoint cap applies to legacy-contract kits only (in_min >= -40 and W_t <= 20);
# contract kits go to in-flow hold repair, and sign-off FF hold >= 0 stays the gate.
set hg_lim [expr {-100.0 + min(0.0, $hg_cin + 40.0, -1.0 * $hg_win)}]
set hg_legacy [expr {$hg_cin >= -40.0 && $hg_win <= 20.0}]
puts "OT_HOLD_GATE structural limit $hg_lim (contract in_min $hg_cin, tap window $hg_win, endpoint cap [expr {$hg_legacy ? 2000 : {none}}])"
# COORD 11-01 05:1x / OWNER 12.28b (closure first): the post-CTS / pre-repair FF hold check is INFO; the one hard stop
# is FF hold WNS worse than OT_HOLD_STOP_PS = -200 ps (structural, not repairable by hold padding).  Hold is judged
# at the routed sign-off (FF hold >= 0 ps on real views, OWNER 11-02).  Same constant in tools/die_plan/hold_gate.tcl,
# tools/orfs_hold_mm.tcl and physical/die_plan/hbm_arch_cores/hold_gate.tcl (test_hold_structural_gate pins it).
# The limit/cap above is that pre-repair screen (reported).  Like the FLOW-19 limit, the stop counts from the kit's
# contract (in_min, tap window W_t: the SDC shifts every such endpoint by the same amount), so it is never stricter
# than main's limit: stop = OT_HOLD_STOP_PS + min(0, in_min + 40, -W_t).  OT_HOLD_PREROUTE_STOP=1 restores the old stop.
# COORD 11-05 07:36: default stop -200 (was -150): GRT hold repair closed 9 of 11 kits from -109 to -172 (DIE-HBM-70 07:04); routed sign-off still decides.
set OT_HOLD_STOP_PS -200.0
# DIE-HEAD-59 11-03 opt-in per kit (item_env): a kit whose only failures past the stop are a few measured port endpoints
# that padding can fix (HEAD hd_ctl_n arst_n/start_i -214 ps, 2 of 1130) goes on to repair; sign-off still decides.
if {[info exists ::env(OT_HOLD_STOP_PS)] && $::env(OT_HOLD_STOP_PS) ne ""} { set OT_HOLD_STOP_PS $::env(OT_HOLD_STOP_PS) }
set hg_stop_lim [expr {$OT_HOLD_STOP_PS + min(0.0, $hg_cin + 40.0, -1.0 * $hg_win)}]
set hg_stop [expr {[info exists ::env(OT_HOLD_PREROUTE_STOP)] && $::env(OT_HOLD_PREROUTE_STOP) eq "1"}]
set hg_screen [expr {$w < $hg_lim || ($hg_legacy && $n > 2000)}]
# KW-FIX-17 11-05 (COORD 16:2x class, same scope as tools/orfs_hold_mm.tcl ot_hold_rr_stats and
# physical/die_plan/hbm_arch_cores/hold_gate.tcl): the structural stop counts register-to-register FF hold only.  In/out-
# port hold paths (timed against the kit's boundary vclk/seam contract) are an ADVISORY line + report; die STA checks
# them against the parent's measured arrivals.  Trigger: HEAD hd_ctl_n stopped post-CTS at FF -281.50 / 1175 with 1090
# forwarded ring inputs on the -250 stop.  The split fails closed (all-path stop) when unavailable.
# OT_HOLD_STOP_SCOPE=all restores the all-path stop.
proc ot_hg_rr_stats {} {
  set w 1e6; set n 0; set ps {}
  if {[catch {
    set ck [all_registers -clock_pins]; set d [all_registers -data_pins]
    if {[llength $ck] && [llength $d]} {
      set ps [find_timing_paths -path_delay min -from $ck -to $d -group_path_count 1000000 -endpoint_path_count 1 -slack_max 0]
    }
  } err]} {
    puts "OT_HOLD_PORT: register-to-register split unavailable ($err); the stop counts all paths"
    return {}
  }
  foreach p $ps { set s [get_property $p slack]; if {$s ne "INF" && $s < 0} { incr n; if {$s < $w} { set w $s } } }
  return [list $w $n]
}
set hg_port_only 0
set hg_scope_all [expr {[info exists ::env(OT_HOLD_STOP_SCOPE)] && $::env(OT_HOLD_STOP_SCOPE) eq "all"}]
if {$w < $hg_stop_lim && !$hg_scope_all} {
  set hg_rr [ot_hg_rr_stats]
  if {[llength $hg_rr] == 2} {
    lassign $hg_rr hg_wrr hg_nrr
    if {$hg_wrr >= $hg_stop_lim} {
      if {$hg_nrr > 0} { set hg_srr [format %.2f $hg_wrr] } else { set hg_srr "-" }
      set hg_adv [format "OT_HOLD_PORT ADVISORY stage=post_cts: FF hold ws %.2f ps over %d endpoints includes in/out-port paths; register-to-register ws %s over %d endpoints; the structural stop %.1f counts register-to-register only (port hold -> die STA against parent arrivals)" $w $n $hg_srr $hg_nrr $hg_stop_lim]
      puts $hg_adv
      if {[info exists ::env(REPORTS_DIR)] && $::env(REPORTS_DIR) ne "" && [file isdirectory $::env(REPORTS_DIR)]} {
        catch {set f [open [file join $::env(REPORTS_DIR) ot_hold_port_advisory_post_cts.rpt] w]; puts $f $hg_adv; close $f}
      }
      set hg_port_only 1
    }
  }
}
if {$w < $hg_stop_lim && !$hg_port_only} {
  puts [format "OT_HOLD_GATE FAIL FF wns_ps %.2f endpoints %d (true negative slack): beyond the structural stop %.1f ps (OT_HOLD_STOP_PS %.0f from contract)" $w $n $hg_stop_lim $OT_HOLD_STOP_PS]
  error "structural FF hold failure: revise plan/RTL/boundary before repair"
}
if {$hg_screen && $hg_stop} {
  puts [format "OT_HOLD_GATE FAIL FF wns_ps %.2f endpoints %d (true negative slack)" $w $n]
  error "structural FF hold failure: revise plan/RTL/boundary before repair"
}
if {$hg_screen} {
  puts [format "OT_HOLD_GATE INFO FF wns_ps %.2f endpoints %d (true negative slack): beyond the pre-repair screen, information only; repair_timing -hold and the routed FF hold sign-off decide" $w $n]
} else {
  puts [format "OT_HOLD_GATE PASS FF wns_ps %.2f endpoints %d (true negative slack)" $w $n]
}
