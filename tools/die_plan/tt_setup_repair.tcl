# tt_setup_repair.tcl (FABLE-PD-HEAD-1650 finding 1, COORD r190): setup repair in a TT scene.
# Class: every kit (S81, QC, KV, HEAD; 65 recent kits read) runs CTS with SKIP_CTS_REPAIR_TIMING=1 and the GRT-stage repair_timing in an
# FF-only session (read_liberty -corner bc): "RSZ-0098 No setup violations found" while the TT gate of the same DB reads -77.72 / -261.02.
# TT setup is measured, never optimised.  This step runs between CTS and GRT (run_kit.sh, only when the kit has tt_setup_repair.on, gen env
# OT_TT_SETUP_REPAIR=1): open 4_cts.odb with the TC libraries and the kit SDC with the vclk bound for TT (the postcts_gate.tcl frame),
# repair_timing -setup only (hold repair stays in the FF GRT session; SETUP_SLACK_MARGIN is NOT used: the hold call shares it), legalize,
# write the repaired 4_cts.odb.  env ODB (input), OUT (output, default = ODB), OT_TT_SETUP_MARGIN (ps, default 0), OT_TT_SETUP_ARGS (extra).
# env OT_TT_SETUP_RC = placement (default, the CTS stage) | grt (5_1_grt.odb: estimate_parasitics -global_routing, the RC basis the TT gate reads;
# measured on hd_host_e v1k2 by HEAD-HOST-CLOSE-1115: GRT RC -77.72 -> -30.40 ps, placement RC -23.70 -> -5.80 ps).
# FABLE-FIX-QC-HCFE 11-15 (r228 item 1; lanes/FABLE-PD-QC-S4q8.md section 2), all three keys opt-in, read from the env or the kit config.mk:
#   OT_TT_SETUP_CSCALE  (grt basis only) multiplies the per-layer C of OT_TT_SETUP_CLAYERS (default M2..M7) for THIS session.  The kit
#     layer table is the clock-arrival fit; routed signal nets carry more C: QC sle_hc2 S3R a3 reads +2.48 / 0 endpoints at x1.0,
#     -155 / 314 at x1.4, -194 / 537 at x1.5, routed sign-off -178.75 / 494; S81 bksel fits x1.40.  The repair then sees the routed load.
#   OT_TT_SETUP_DESIGN=1 runs repair_design (TT slew / cap) before repair_timing: the kit's GRT repair_design is an FF session
#     (sle_hc2: 6 slew violations there, 465 at TT sign-off).
#   OT_TT_SETUP_MARGIN  (ps) is now also read from config.mk.
if {[file exists /work/config.mk]} {
  set fh [open /work/config.mk]
  foreach ln [split [read $fh] "\n"] {
    if {[regexp {^export\s+(OT_VCLK_TT|LAYER_PARASITICS_FILE|OT_TT_SETUP_MARGIN|OT_TT_SETUP_CSCALE|OT_TT_SETUP_CLAYERS|OT_TT_SETUP_DESIGN|OT_RC_SIGNAL|OT_RC_SIGNAL_SCALE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} { set ::env($k) $v }
  }
  close $fh
}
proc ot_tt_libs {} {
  set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=/work/config.mk" "print-TC_LIB_FILES"}]
  set recs {}
  foreach line [split $output \n] { if {[regexp {^TC_LIB_FILES\s*[:=]\s*(.*)$} $line -> v]} { lappend recs $v } }
  if {[llength $recs] != 1} { error "tt_setup_repair: missing or ambiguous make TC_LIB_FILES" }
  return [regexp -all -inline {\S+} [lindex $recs 0]]
}
foreach f [ot_tt_libs] {
  set g [file join [file dirname [file dirname $f]] .busfit [file tail $f]]
  if {[file exists $g]} { set c [open $g]; gets $c h; close $c; if {[string first [lindex [exec sha256sum -- $f] 0] $h] >= 0} { set f $g } }
  read_liberty $f
}
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set virt {}; set real {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend virt $c } else { lappend real $c } }
if {[llength $virt] != 1} { error "tt_setup_repair: expected exactly one source-less virtual IO clock" }
if {[info exists ::env(OT_VCLK_TT)]} { set_clock_latency -source $::env(OT_VCLK_TT) $virt }
set_propagated_clock $real
if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} { source $::env(LAYER_PARASITICS_FILE) } else { source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl }
set ot_tt_rc placement; if {[info exists ::env(OT_TT_SETUP_RC)] && $::env(OT_TT_SETUP_RC) eq "grt"} { set ot_tt_rc grt }
set ot_tt_cs 1.0
if {[info exists ::env(OT_TT_SETUP_CSCALE)] && $::env(OT_TT_SETUP_CSCALE) ne ""} {
  if {![string is double -strict $::env(OT_TT_SETUP_CSCALE)] || $::env(OT_TT_SETUP_CSCALE) <= 0} { error "tt_setup_repair: bad OT_TT_SETUP_CSCALE $::env(OT_TT_SETUP_CSCALE)" }
  set ot_tt_cs $::env(OT_TT_SETUP_CSCALE)
}
if {$ot_tt_rc eq "grt" && $ot_tt_cs != 1.0} {
  # re-issue the layer table of the file just sourced with C x scale on the signal routing layers (R and vias unchanged)
  set ot_tt_rcf /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
  if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} { set ot_tt_rcf $::env(LAYER_PARASITICS_FILE) }
  set ot_tt_cl {M2 M3 M4 M5 M6 M7}
  if {[info exists ::env(OT_TT_SETUP_CLAYERS)] && $::env(OT_TT_SETUP_CLAYERS) ne ""} { set ot_tt_cl [split $::env(OT_TT_SETUP_CLAYERS) ,] }
  set fh [open $ot_tt_rcf]; set ot_tt_rct [read $fh]; close $fh
  set ot_tt_cn 0
  foreach ln [split $ot_tt_rct "\n"] {
    if {![regexp {^\s*set_layer_rc\s} $ln] || ![regexp {\s-layer\s+(\S+)} $ln -> l] || $l ni $ot_tt_cl} continue
    if {![regexp {\s-resistance\s+(\S+)} $ln -> r] || ![regexp {\s-capacitance\s+(\S+)} $ln -> c]} continue
    set_layer_rc -layer $l -resistance $r -capacitance [expr {$c * $ot_tt_cs}]
    incr ot_tt_cn
  }
  if {$ot_tt_cn != [llength $ot_tt_cl]} { error "tt_setup_repair: OT_TT_SETUP_CSCALE found $ot_tt_cn of [llength $ot_tt_cl] layers in $ot_tt_rcf" }
  puts "OT_TT_SETUP_REPAIR signal C x$ot_tt_cs on $ot_tt_cn layers ($ot_tt_cl) for this session"
}
set ot_tt_design [expr {[info exists ::env(OT_TT_SETUP_DESIGN)] && $::env(OT_TT_SETUP_DESIGN) eq "1"}]
proc ot_tt_est {} {
  global ot_tt_rc
  if {$ot_tt_rc eq "grt"} { estimate_parasitics -global_routing } else { estimate_parasitics -placement }
}
# FABLE-FIX-S81-STRIP / OWNER r703 11-18 (RSZ-0074 on t15 / t16 / t26): after repair_timing + detailed_placement the incremental global route can leave a partial tree on a net it
# changed ('found route to N pins, expected M') and the estimate that follows dies, so the kit kept the UNREPAIRED DB.  The step now repairs the ROUTE and keeps the repaired DB:
# (1) route the dirty nets again (start / end incremental), (2) a full global_route, each followed by the estimate.  Only when both fail does the error propagate (the run_kit step then
# keeps the old DB with a logged WARNING).
proc ot_tt_est_after_repair {} {
  global ot_tt_rc
  if {$ot_tt_rc ne "grt"} { ot_tt_est; return }
  if {![catch {ot_tt_est} err]} { return }
  if {![string match "*RSZ-0074*" $err]} { error $err }
  puts "OT_TT_SETUP_REPAIR WARNING RSZ-0074 after the repair ($err): re-routing the repaired nets"
  if {![catch {global_route -start_incremental -allow_congestion; global_route -end_incremental -allow_congestion; ot_tt_est} err2]} {
    puts "OT_TT_SETUP_REPAIR RSZ-0074 cleared by an incremental re-route"
    return
  }
  puts "OT_TT_SETUP_REPAIR WARNING incremental re-route did not clear it ($err2): full global_route"
  if {![catch {global_route -allow_congestion; ot_tt_est} err3]} {
    puts "OT_TT_SETUP_REPAIR RSZ-0074 cleared by a full global_route"
    return
  }
  error "RSZ-0074 persists after incremental and full global_route: $err3"
}
ot_tt_est
# r222 (opt-in OT_RC_SIGNAL=1, GRT basis only): signal nets at the routed-RCX signal unit C (rc_signal_adjust.tcl)
if {$ot_tt_rc eq "grt" && [info exists ::env(OT_RC_SIGNAL)] && $::env(OT_RC_SIGNAL) eq "1" && [file exists /work/rc_signal_adjust.tcl]} { source /work/rc_signal_adjust.tcl; ot_rc_signal_table }
puts "OT_TT_SETUP_REPAIR rc basis $ot_tt_rc"
proc ot_tt_wns {tag} {
  set w [sta::worst_slack -max]; set t [sta::total_negative_slack -max]
  puts [format "OT_TT_SETUP_REPAIR %s TT setup wns %.2f tns %.2f" $tag $w $t]
  return [list $w $t]
}
# r268 (FABLE-FIX-HEAD-TYPES, hd_serdes sd2): OT_TT_SETUP_MEASURE=1 only reads the TT setup wns/tns of ODB in this same frame and exits;
# the run_kit step uses it on the WRITTEN repaired DB (a fresh session = what every later reader sees) before keeping it.
if {[info exists ::env(OT_TT_SETUP_MEASURE)] && $::env(OT_TT_SETUP_MEASURE) eq "1"} {
  ot_tt_wns measure
  exit 0
}
lassign [ot_tt_wns before] w0 t0
set mg 0; if {[info exists ::env(OT_TT_SETUP_MARGIN)] && $::env(OT_TT_SETUP_MARGIN) ne ""} { set mg $::env(OT_TT_SETUP_MARGIN) }
set extra {}; if {[info exists ::env(OT_TT_SETUP_ARGS)]} { set extra $::env(OT_TT_SETUP_ARGS) }
set n0 [llength [get_cells *]]
if {$w0 < $mg || $ot_tt_design} {
  # GRT-RC mode works on a routed-guide DB: route the changed nets incrementally (as ORFS wraps repair_timing in the GRT stage) so every
  # new buffer / resized net keeps a guide for detail route; -allow_congestion = the kit's own GRT policy (GRT-0232 class)
  if {$ot_tt_rc eq "grt"} {
    source /work/grt_pg_replay.tcl
    ot_grt_pg_replay_begin /work
    global_route -start_incremental -allow_congestion
  }
  if {$ot_tt_design} {
    repair_design -verbose
    ot_tt_wns after_design
  }
  # r268: the GRT-stage pass must not rebuild fanouts the place stage split (sd2: 26 buffers removed, 11 pins / 20 fF -> 42 pins / 103 fF = +412 ps);
  # -skip_buffer_removal unless the caller's OT_TT_SETUP_ARGS already says so
  if {$ot_tt_rc eq "grt" && [lsearch -exact $extra -skip_buffer_removal] < 0} { lappend extra -skip_buffer_removal }
  repair_timing -setup -setup_margin $mg -repair_tns 100 -skip_last_gasp -verbose {*}$extra
  detailed_placement
  if {$ot_tt_rc eq "grt"} {
    global_route -end_incremental -allow_congestion
    ot_grt_pg_replay_end
  }
  ot_tt_est_after_repair
  if {$ot_tt_rc eq "grt" && [info exists ::env(OT_TT_SETUP_GUIDE)] && $::env(OT_TT_SETUP_GUIDE) ne ""} { write_guides $::env(OT_TT_SETUP_GUIDE) }     # after any re-route, so the guide holds the final routes
}
lassign [ot_tt_wns after] w1 t1
puts "OT_TT_SETUP_REPAIR cells [expr {[llength [get_cells *]] - $n0}] added; wns [format %.2f $w0] -> [format %.2f $w1] tns [format %.2f $t0] -> [format %.2f $t1]"
set out $::env(ODB); if {[info exists ::env(OUT)] && $::env(OUT) ne ""} { set out $::env(OUT) }
write_db $out
puts "OT_TT_SETUP_REPAIR wrote $out"
