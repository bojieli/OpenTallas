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
if {![llength [info commands ot_cf_pinregs]]} { error "OT_POSTCTS_GATE: clock_family.tcl (ot_cf_pinregs) not loaded" }
set bnd [ot_cf_pinregs]
set arr {}
set grp {}
dict for {i p} $bnd {
  # same measure as the sign-off clock check (clock_family.tcl: active-edge propagated clock arrival)
  set a [ot_cf_pinreg_arrival $p [get_clocks clk] $per]
  if {$a eq ""} continue
  lappend arr $a
  # leaf group = the net driving the pin-register clock pin (the unit a re-tap / pad acts on)
  set g "?"
  catch {set g [get_full_name [get_nets -of_objects $p]]}
  dict lappend grp $g $a
}
set n [llength $arr]
set mean [expr {$n ? [tcl::mathop::+ {*}$arr] / $n : -1}]
set arr [lsort -real $arr]
set ws [expr {[sta::worst_slack_cmd max] * 1e12}]
set hs [expr {[sta::worst_slack_cmd min] * 1e12}]
set dev [expr {$n ? abs($mean - $bound) : 1e9}]
set v [expr {$n && $dev <= $tol ? "PASS" : "FAIL"}]
# rule LC1 window (CLOCK-RESET 10-25): EVERY pin register within bound +- OT_POSTCTS_WIN_PS (default = tol) at this
# corner, and every leaf group's max-min <= OT_POSTCTS_GRP_SPREAD_PS (default 20, the MSCTS balance).  A mean inside
# tol with a tail 20-60 ps late is the late-capture class (input hold -30..-170 at FF on CP1/KV io_ft/t12/coll_ftm/head).
# Reported always; it changes the verdict only with OT_POSTCTS_WINDOW=1 (batched default-on, change control).
set win [expr {[info exists ::env(OT_POSTCTS_WIN_PS)] ? $::env(OT_POSTCTS_WIN_PS) : $tol}]
set gsp [expr {[info exists ::env(OT_POSTCTS_GRP_SPREAD_PS)] ? $::env(OT_POSTCTS_GRP_SPREAD_PS) : 20.0}]
set late 0; set early 0
foreach a $arr { if {$a > $bound + $win} { incr late } elseif {$a < $bound - $win} { incr early } }
set wide 0; set gmax 0.0
dict for {g as} $grp {
  set as [lsort -real $as]; set sp [expr {[lindex $as end] - [lindex $as 0]}]
  if {$sp > $gmax} { set gmax $sp }
  if {$sp > $gsp} { incr wide }
}
set wv [expr {$n && $late == 0 && $early == 0 && $wide == 0 ? "PASS" : "FAIL"}]
if {[info exists ::env(OT_POSTCTS_WINDOW)] && $::env(OT_POSTCTS_WINDOW) && $wv ne "PASS"} { set v FAIL }
set fh [open /work/postcts_gate_${c}.json w]
puts $fh [format "{\"corner\": \"%s\", \"pinreg_n\": %d, \"pinreg_mean_ps\": %.2f, \"pinreg_min_ps\": %.2f, \"pinreg_max_ps\": %.2f, \"bound_ps\": %.2f, \"dev_ps\": %.2f, \"tol_ps\": %.1f, \"setup_wns_est_ps\": %.2f, \"hold_wns_est_ps\": %.2f, \"rc\": \"%s\", \"parasitics\": \"%s\", \"win_ps\": %.1f, \"late_n\": %d, \"early_n\": %d, \"groups\": %d, \"group_spread_max_ps\": %.2f, \"groups_wide\": %d, \"window\": \"%s\", \"verdict\": \"%s\"}" \
  $C $n $mean [expr {$n ? [lindex $arr 0] : -1}] [expr {$n ? [lindex $arr end] : -1}] $bound $dev $tol $ws $hs \
  [expr {[info exists ::env(LAYER_PARASITICS_FILE)] ? $::env(LAYER_PARASITICS_FILE) : "platform setRC.tcl"}] $ot_pg_mode \
  $win $late $early [dict size $grp] $gmax $wide $wv $v]
close $fh
puts [format "OT_POSTCTS_GATE %s (%s) pinreg n %d mean %.2f bound %.2f dev %.2f tol %.1f setup_est %.2f hold_est %.2f %s" \
  $C $ot_pg_mode $n $mean $bound $dev $tol $ws $hs $v]
puts [format "OT_POSTCTS_WINDOW %s pinreg late %d early %d (bound +-%.1f) groups %d spread max %.2f wide %d (> %.1f) %s%s" \
  $C $late $early $win [dict size $grp] $gmax $wide $gsp $wv [expr {[info exists ::env(OT_POSTCTS_WINDOW)] && $::env(OT_POSTCTS_WINDOW) ? " (enforced)" : " (report)"}]]
