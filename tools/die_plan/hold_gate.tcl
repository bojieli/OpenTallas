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
set hg_gold [file join [file dirname [file normalize [info script]]] constraint.sdc]
if {[info exists ::env(OT_GOLDEN_SDC)] && $::env(OT_GOLDEN_SDC) ne ""} { set hg_gold $::env(OT_GOLDEN_SDC) }
if {[file exists $hg_gold]} {
  set f [open $hg_gold]; set hg_txt [read $f]; close $f
  foreach line [split $hg_txt "\n"] {
    # S81-RINGHOLD-3 opt-in plan clock.ring_hold: the measured sender data-vs-fclk min replaces the seam fallback
    if {[regexp {^# OT_FWD_RING_MIN (\S+)$} $line -> hg_ring_in]} continue
    if {![string match {# OT_FWD_RING_INPUTS *} $line]} continue
    set w [regexp -all -inline {\S+} $line]
    if {[llength $w] < 4} { error "hold gate: malformed OT_FWD_RING_INPUTS line: $line" }
    lappend hg_fwd [list [lindex $w 2] [lrange $w 3 end]]
    foreach s [lrange $w 3 end] { foreach q [get_ports $s] { lappend hg_fwd_ports [get_full_name $q] } }
  }
}
set din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $clock_ports && [get_full_name $p] ni $hg_fwd_ports} { lappend din $p } }
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
set hg_lim [expr {-100.0 + min(0.0, $hg_cin + 40.0)}]
puts "OT_HOLD_GATE structural limit $hg_lim (contract in_min $hg_cin)"
# DIE-HEAD-53 (opt-in OT_HOLD_WINDOW_SPLIT=1, kits with a plan clock.tap_window W > 0): the window is a plan contract
# (die tap-to-tap arrival spread, DIE-HEAD-51 W_t = ceil10(die damage + 10)), charged in full on EVERY flop pair whose
# launch and capture hang on two different tap ports (launch -W early, capture 0 late; OpenSTA has no CPPR across
# ports).  It is planned hold demand that in-flow hold repair closes, not a structural fault of the kit (HEAD l48y
# hd_tile: 9584 of 11952 endpoints are cross-tap pairs 35 um apart, -161.8 with W 130; re-timed without the window the
# kit is -31.8 internal / 1100 endpoints).  With the split the gate judges:
#   structural = the same kit re-timed with the window lines of the kit SDC at 0: ws >= lim, internal (non-input
#                startpoint) endpoints <= 2000; input-port endpoints are planned input demand (FLOW-SHARED-5), reported;
#   contract   = the real SDC: ws >= lim - W (nothing beyond what the declared window explains).
# Off (default): unchanged.  The SDC, the window and the repair corner are never changed by the gate.
proc hg_window_lines {txt win} {
  set out {}
  foreach line [split $txt "\n"] {
    if {[regexp {^set_clock_latency\s+-source\s+-early\s+(-clock\s+\S+\s+)?(-?[0-9.]+)\s+\[get_ports\s+\{([^\}]*)\}\]} $line -> ck v ports]
        && abs($v + $win) < 1e-6} { lappend out [list [string trim $ck] $ports] }
  }
  return $out
}
set hg_split [expr {[info exists ::env(OT_HOLD_WINDOW_SPLIT)] && $::env(OT_HOLD_WINDOW_SPLIT) eq "1" && $hg_win > 0}]
if {$hg_split && ($w < $hg_lim || $n > 2000)} {
  set hg_wl {}
  if {[info exists hg_txt]} { set hg_wl [hg_window_lines $hg_txt $hg_win] }
  if {![llength $hg_wl]} { error "hold gate: OT_HOLD_WINDOW_SPLIT=1 but no 'set_clock_latency -source -early -$hg_win' window line in the kit SDC" }
  foreach l $hg_wl { set_clock_latency -source -early {*}[lindex $l 0] 0 [get_ports [lindex $l 1]] }
  set w0 [sta::time_sta_ui [sta::worst_slack_cmd min]]
  set n0 [sta::endpoint_violation_count min]
  set hg_inp [dict create]
  foreach p [all_inputs] { dict set hg_inp [get_full_name $p] 1 }
  set ni 0; set np 0; set wi 1e9; set wp 1e9
  foreach pa [find_timing_paths -path_delay min -group_path_count 1000000 -endpoint_path_count 1 -slack_max 0] {
    set s [sta::time_sta_ui [get_property $pa slack]]
    if {$s >= 0} continue
    if {[dict exists $hg_inp [get_full_name [get_property $pa startpoint]]]} { incr np; set wp [expr {min($wp, $s)}] } else { incr ni; set wi [expr {min($wi, $s)}] }
  }
  set hg_clim [expr {$hg_lim - $hg_win}]
  set swi -; set swp -
  if {$ni} { set swi [format %.2f $wi] }; if {$np} { set swp [format %.2f $wp] }
  puts [format "OT_HOLD_GATE WINDOW_SPLIT W %g: contract wns_ps %.2f endpoints %d (limit %g); structural (window 0) wns_ps %.2f endpoints %d = internal %d (ws %s) + planned input %d (ws %s) (limits ws >= %g, internal <= 2000)" \
    $hg_win $w $n $hg_clim $w0 $n0 $ni $swi $np $swp $hg_lim]
  if {$w >= $hg_clim && $w0 >= $hg_lim && $ni <= 2000} {
    puts [format "OT_HOLD_GATE PASS FF wns_ps %.2f endpoints %d (true negative slack; window-split: planned window/input demand %d endpoints -> repair)" $w $n $n]
    return
  }
}
if {$w < $hg_lim || $n > 2000} {
  puts [format "OT_HOLD_GATE FAIL FF wns_ps %.2f endpoints %d (true negative slack)" $w $n]
  error "structural FF hold failure: revise plan/RTL/boundary before repair"
}
puts [format "OT_HOLD_GATE PASS FF wns_ps %.2f endpoints %d (true negative slack)" $w $n]
