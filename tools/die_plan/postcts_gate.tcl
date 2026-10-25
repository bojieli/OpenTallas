# postcts_gate.tcl -- FLOW 2026-10-25 post-CTS gate before route (GEOM-REVIEW / GEOM-REVIEW-2 [FLOW] 05:00).
# One corner per run (env OT_CORNER = TT | FF): 4_cts.odb, kit SDC with the vclk bound for THAT corner
# (OT_VCLK_TT / OT_VCLK_FF), placement parasitics on the kit's RC basis (LAYER_PARASITICS_FILE, the RCX-calibrated
# setRC_rcx.tcl by default), propagated clocks.  Pin-register set = the registers the sign-off clock check uses
# (fanout of the data inputs, fanin of the outputs).  Writes /work/postcts_gate_<corner>.json:
#   pin-reg CK arrival mean / min / max / n, bound I, |mean - bound|, setup / hold WNS (estimate), verdict.
# Verdict FAIL when |mean - bound| > OT_POSTCTS_TOL (default 20 ps): the route would carry a wrong I into sign-off.
set C $::env(OT_CORNER)
# outside make (runner calls openroad directly): take the kit exports from /work/config.mk
if {[file exists /work/config.mk]} {
  set fh [open /work/config.mk]
  foreach ln [split [read $fh] "\n"] {
    if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} {
      set ::env($k) $v
    }
  }
  close $fh
}
set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_sdc /work/constraint.sdc
set bound [expr {$C eq "FF" ? $::env(OT_VCLK_FF) : $::env(OT_VCLK_TT)}]
set tol [expr {[info exists ::env(OT_POSTCTS_TOL)] ? $::env(OT_POSTCTS_TOL) : 20.0}]
set vck [lsearch -all -inline -not [all_clocks] [get_clocks clk]]
if {[llength $vck] == 1} { set_clock_latency -source $bound $vck }
if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} {
  source $::env(LAYER_PARASITICS_FILE)
} else {
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
}
# 5_1_grt.odb carries the global routes: use them (the basis the RCX calibration was fitted on, est - RCX <= 5 ps);
# a CTS / placement odb falls back to the placement estimate (set_wire_rc), which the 10-25 rr_h0 check showed to read
# the pin-register clock ~75 ps EARLY against routed RCX (188 vs 263.7) -> informational only.
set ot_pg_mode placement
if {[info exists ::env(OT_POSTCTS_GRT)] && $::env(OT_POSTCTS_GRT) && ![catch {estimate_parasitics -global_routing}]} {
  set ot_pg_mode global_routing
} else {
  estimate_parasitics -placement
}
set_propagated_clock [get_clocks clk]
set per [get_property [get_clocks clk] period]
foreach cf [list /work/clock_family.tcl [file join [file dirname [info script]] clock_family.tcl]] {
  if {[file exists $cf]} { source $cf; break }
}
if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
# pin-register set + measure: pinreg_measure.tcl (the same procs pinreg_pad.tcl, the GRT pre-pass pad, uses)
foreach pm [list /work/pinreg_measure.tcl [file join [file dirname [info script]] pinreg_measure.tcl]] {
  if {[file exists $pm]} { source $pm; break }
}
set arr {}
dict for {i p} [ot_pinreg_set] {
  set a [ot_pinreg_arr $p [get_clocks clk]]
  if {$a ne ""} { lappend arr $a }
}
set n [llength $arr]
set mean [expr {$n ? [tcl::mathop::+ {*}$arr] / $n : -1}]
set arr [lsort -real $arr]
set ws [expr {[sta::worst_slack_cmd max] * 1e12}]
set hs [expr {[sta::worst_slack_cmd min] * 1e12}]
set dev [expr {$n ? abs($mean - $bound) : 1e9}]
set v [expr {$n && $dev <= $tol ? "PASS" : "FAIL"}]
set fh [open /work/postcts_gate_${c}.json w]
puts $fh [format "{\"corner\": \"%s\", \"pinreg_n\": %d, \"pinreg_mean_ps\": %.2f, \"pinreg_min_ps\": %.2f, \"pinreg_max_ps\": %.2f, \"bound_ps\": %.2f, \"dev_ps\": %.2f, \"tol_ps\": %.1f, \"setup_wns_est_ps\": %.2f, \"hold_wns_est_ps\": %.2f, \"rc\": \"%s\", \"parasitics\": \"%s\", \"verdict\": \"%s\"}" \
  $C $n $mean [expr {$n ? [lindex $arr 0] : -1}] [expr {$n ? [lindex $arr end] : -1}] $bound $dev $tol $ws $hs \
  [expr {[info exists ::env(LAYER_PARASITICS_FILE)] ? $::env(LAYER_PARASITICS_FILE) : "platform setRC.tcl"}] $ot_pg_mode $v]
close $fh
puts [format "OT_POSTCTS_GATE %s (%s) pinreg n %d mean %.2f bound %.2f dev %.2f tol %.1f setup_est %.2f hold_est %.2f %s" \
  $C $ot_pg_mode $n $mean $bound $dev $tol $ws $hs $v]
