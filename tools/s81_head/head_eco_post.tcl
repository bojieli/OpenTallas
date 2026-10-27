# HEAD-CORE-R14 2026-10-27 (COORD RULING HEAD-CORE-R13 ASK3): POST_GLOBAL_ROUTE hook of the warm post-route ECO of a
# ROUTED s81_head hard core (head_post_route_eco.sh).  The do-5_1_grt that sources this starts from the core's own
# 5_2_route.odb (copied in as 4_cts.odb) with that route's RCX 6_final.spef in RESULTS_DIR.
# Order (KV-CORES eco_route.tcl recipe, the order that signed the KV e1/e5/e7 cores):
#   read routed RCX SPEF -> repair_design (max fanout 24, slew/cap margin OT_SLEW_MARGIN %) -> repair_timing -setup
#   (margin OT_SETUP_MARGIN) -> repair_timing -hold (margin OT_HOLD_MARGIN; HB4xp67 is the ONLY extra hold cell,
#   hold_pad_hb4.tcl + r10_hold_pass2_hook.tcl installed by the kit's PRE_GLOBAL_ROUTE_TCL bind_ff_actual.tcl,
#   12.4a a1 data-path hold cells) -> legalize -> incremental GRT -> guides; DRT then re-routes the changed nets.
# Clock network untouched (plan-built mscts_h nets are dont_touch; no clock ECO, 12.8d2 not used).
# Frame: the kit PRE hook binds vclk source latency 202.5 (the FF bound the sign-off uses) for the repair; the TT 250
# contract latency is restored before ORFS writes 5_1_grt.sdc, and the chain then installs constraint.sdc anyway.
proc hd_eco_counts {tag} {
  puts [format "HEAD_ECO_%s setup_ps %.3f hold_ps %.3f setup_n %d hold_n %d max_slew_n %d max_cap_n %d" $tag \
    [sta::time_sta_ui [sta::worst_slack_cmd max]] [sta::time_sta_ui [sta::worst_slack_cmd min]] \
    [sta::endpoint_violation_count max] [sta::endpoint_violation_count min] \
    [sta::max_slew_violation_count] [sta::max_capacitance_violation_count]]
}
set ::hd_eco_t0 [clock seconds]
puts "HEAD_ECO_START OT_SLEW_MARGIN $::env(OT_SLEW_MARGIN) OT_SETUP_MARGIN $::env(OT_SETUP_MARGIN) OT_HOLD_MARGIN $::env(OT_HOLD_MARGIN)"
read_spef $::env(RESULTS_DIR)/6_final.spef
hd_eco_counts PRE_RCX
source /work/eco_route.tcl
hd_eco_counts POST_GRT_EST
set n 0
foreach i [get_cells -quiet -hierarchical *] { if {[get_property $i ref_name] eq "HB4xp67_ASAP7_75t_R"} { incr n } }
puts "HEAD_ECO_HB4 total $n elapsed_s [expr {[clock seconds] - $::hd_eco_t0}]"
set_clock_latency -source 250.0 [get_clocks vclk]
puts "HEAD_ECO_DONE vclk source latency restored to the TT 250 contract"
