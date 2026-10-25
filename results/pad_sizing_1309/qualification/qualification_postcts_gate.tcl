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
    if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE|OT_PINREG_GROUP_GUARD|OT_PINREG_HOLD_CENSUS|OT_TAP_GRT_PRE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} {
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
# a CTS / placement odb falls back to the placement estimate (set_wire_rc) -> informational only.
# Propagated clocks BEFORE estimate_parasitics: rsz -placement skips nets driven from an ideal clock, so estimating
# first left the clock tree with no wire RC and read the pin-register CK ~55-62 ps early (KITS-SPARE ve_m 193 vs 316,
# FLOW 09:41 10-25; the earlier "placement reads ~75 ps early" rr_h0 note was this).  FLOW-INFRA-2 A/B 10-25 on the
# head + KV canary 5_1_grt.odb: -global_routing is order-independent (bit-identical); fixed placement reads +10..+13 ps.
set_propagated_clock [get_clocks clk]
set ot_pg_mode placement
if {[info exists ::env(OT_POSTCTS_GRT)] && $::env(OT_POSTCTS_GRT) && ![catch {estimate_parasitics -global_routing}]} {
  set ot_pg_mode global_routing
} else {
  estimate_parasitics -placement
}
set per [get_property [get_clocks clk] period]
foreach cf [list /work/clock_family.tcl [file join [file dirname [info script]] clock_family.tcl]] {
  if {[file exists $cf]} { source $cf; break }
}
if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
if {![llength [info commands ot_cf_pinregs]]} { error "postcts_gate: canonical pin-register collector missing" }
set bnd [ot_cf_pinregs]
set measured [ot_cf_pinreg_measure [get_clocks clk]]
set n [dict get $measured n]
set mean [dict get $measured mean]
set arr [list [dict get $measured min] [dict get $measured max]]
set limits [ot_cf_pinreg_limits [dict get $measured groups] $bound $tol]
set strict_groups [expr {([info exists ::env(OT_PINREG_GROUP_GUARD)] && $::env(OT_PINREG_GROUP_GUARD) eq "1") || ([info exists ::env(OT_TAP_GRT_PRE)] && $::env(OT_TAP_GRT_PRE) eq "1")}]
set census [dict create status NOT_RUN n -1 worst_ps -1 tns_ps -1 margin_n -1]
if {$C eq "FF" && [info exists ::env(OT_PINREG_HOLD_CENSUS)] && $::env(OT_PINREG_HOLD_CENSUS) eq "1"} {
  set census [ot_cf_output_hold_census]
  puts "OT_PINREG_HOLD_CENSUS FF $census"
}
puts "OT_PINREG_GROUPS $C strict $strict_groups $limits"
set ws [expr {[sta::worst_slack_cmd max] * 1e12}]
set hs [expr {[sta::worst_slack_cmd min] * 1e12}]
set dev [expr {$n ? abs($mean - $bound) : 1e9}]
set v [expr {$n && $dev <= $tol && (!$strict_groups || [dict get $limits verdict] eq "PASS") ? "PASS" : "FAIL"}]
set tag [expr {[info exists ::env(OT_POSTCTS_TAG)] ? $::env(OT_POSTCTS_TAG) : "postcts_gate"}]
if {![regexp {^[A-Za-z0-9_]+$} $tag]} { error "postcts_gate: unsafe output tag" }
set fh [open /work/${tag}_${c}.json w]
puts $fh [format "{\"corner\": \"%s\", \"pinreg_n\": %d, \"pinreg_mean_ps\": %.2f, \"pinreg_min_ps\": %.2f, \"pinreg_max_ps\": %.2f, \"bound_ps\": %.2f, \"dev_ps\": %.2f, \"tol_ps\": %.1f, \"setup_wns_est_ps\": %.2f, \"hold_wns_est_ps\": %.2f, \"rc\": \"%s\", \"parasitics\": \"%s\", \"verdict\": \"%s\"}" \
  $C $n $mean [expr {$n ? [lindex $arr 0] : -1}] [expr {$n ? [lindex $arr end] : -1}] $bound $dev $tol $ws $hs \
  [expr {[info exists ::env(LAYER_PARASITICS_FILE)] ? $::env(LAYER_PARASITICS_FILE) : "platform setRC.tcl"}] $ot_pg_mode $v]
close $fh
set original [open /work/${tag}_${c}.json r]; set json [read $original]; close $original
set json [string trimright [string trim $json] "}"]
append json [format ", \"group_min_ps\": %.4f, \"group_max_ps\": %.4f, \"group_spread_ps\": %.4f, \"hold_census_status\": \"%s\", \"hold_census_n\": %d, \"hold_census_worst_ps\": %.4f, \"hold_census_tns_ps\": %.4f, \"hold_census_margin_n\": %d}\n" [dict get $limits min] [dict get $limits max] [dict get $limits spread] [dict get $census status] [dict get $census n] [dict get $census worst_ps] [dict get $census tns_ps] [dict get $census margin_n]]
set original [open /work/${tag}_${c}.json w]; puts -nonewline $original $json; close $original
set detail [open /work/${tag}_${c}.groups.tsv w]
puts $detail "group\tmean_ps\tn\tmin_ps\tmax_ps"
dict for {group values} [dict get $measured groups] {
  puts $detail "$group\t[lindex $values 0]\t[lindex $values 1]\t[lindex $values 3]\t[lindex $values 4]"
}
puts $detail "# limits $limits"
puts $detail "# output_hold $census"
close $detail
puts [format "OT_POSTCTS_GATE %s (%s) pinreg n %d mean %.2f bound %.2f dev %.2f tol %.1f setup_est %.2f hold_est %.2f %s" \
  $C $ot_pg_mode $n $mean $bound $dev $tol $ws $hs $v]
