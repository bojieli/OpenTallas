# QC-A0 10-24 A0 v7 PRE_CTS: the CURRENT die_plan clock tools, unchanged (no private copy as in v4-v6):
#   tools/die_plan/clock_taps.tcl  every sink of ck moves to its nearest tap port (ck / ck_t<i>: R4 grid 2 x 3 at 400 um
#                                  + the v6 sink-anchored additions, gen_a0c7_taps.py), cap OT_TAP_MAX_SINKS per tap,
#                                  re-assignment <= OT_TAP_PITCH_UM / 2; per-tap sink counts + dropped empty taps
#   tools/die_plan/tap_balance.tcl right after clock_tree_synthesis: short trees padded up to the plan insertion
#                                  OT_TAP_TARGET_PS (250), OT_TAP_CHECK on 250 + 40
# The tap port family / SDC clock are passed by env (OT_TAP_PORT ck, OT_TAP_CLOCK core_clk).
if {![info exists ::env(OT_TAP_PORT)]} { set ::env(OT_TAP_PORT) ck }
if {![info exists ::env(OT_TAP_CLOCK)]} { set ::env(OT_TAP_CLOCK) core_clk }
source /src/tools/die_plan/clock_taps.tcl
rename clock_tree_synthesis ::ot_a0_cts_orig
proc clock_tree_synthesis {args} {
  ::ot_a0_cts_orig {*}$args
  source /src/tools/die_plan/tap_balance.tcl
}
