# HEAD-CORE-R14 2026-10-27 (COORD RULING HEAD-CORE-R13 ASK3): POST_GLOBAL_ROUTE hook of the warm post-route ECO of a
# ROUTED s81_head hard core (head_post_route_eco.sh).  The do-5_1_grt that sources this starts from the core's own
# 5_2_route.odb (copied in as 4_cts.odb) with that route's RCX 6_final.spef in RESULTS_DIR.
# Order (KV-CORES eco_route.tcl recipe, the order that signed the KV e1/e5/e7 cores):
#   read routed RCX SPEF -> repair_design (max fanout 24, slew/cap margin OT_SLEW_MARGIN %) -> repair_timing -setup
#   (margin OT_SETUP_MARGIN) -> repair_timing -hold (margin OT_HOLD_MARGIN; HB4xp67 is the ONLY extra hold cell,
#   hold_pad_hb4.tcl + r10_hold_pass2_hook.tcl installed by the PRE_GLOBAL_ROUTE hook bind_ff_eco.tcl,
#   12.4a a1 data-path hold cells) -> legalize -> incremental GRT -> guides; DRT then re-routes the changed nets.
# Clock network untouched (plan-built mscts_h nets are dont_touch; no clock ECO, 12.8d2 not used).
# HEAD-CORE-R17 (per-mode, same fix as R16 for the rebuild): the session is the orfs_hold_mm two-mode session
# (head_eco_modes.py): scene tc (mode ss) = TT setup under constraint.sdc (vclk 250), scene BC (mode ff) = FF hold under
# constraint.sdc + vclk_ff.sdc (vclk 202.5).  ot_mm_sync disables hold in ss and setup in ff for the repair, so
# repair_timing -setup sees only TT setup and -hold only FF hold (no phantom TT hold against the FF vclk).  The routed
# RCX SPEF is read AFTER the sync (the sync re-estimates GRT parasitics).  FAIL-CLOSED: no mm session / no sync -> error.
# The owner 10-25 structural FF hold stop (ot_hold_structural_gate: ws >= -100 ps, <= 2000 endpoints) runs on the RCX
# view before any repair, exactly as at CTS/GRT.
proc hd_eco_counts {tag} {
  puts [format "HEAD_ECO_%s setup_ps %.3f hold_ps %.3f setup_n %d hold_n %d max_slew_n %d max_cap_n %d" $tag \
    [sta::time_sta_ui [sta::worst_slack_cmd max]] [sta::time_sta_ui [sta::worst_slack_cmd min]] \
    [sta::endpoint_violation_count max] [sta::endpoint_violation_count min] \
    [sta::max_slew_violation_count] [sta::max_capacitance_violation_count]]
}
proc hd_eco_scene_ws {} {
  puts [format "HEAD_ECO_MODES tc setup %.3f / BC hold %.3f ps" [ot_mm_ws max [ot_mm_sc]] [ot_mm_ws min BC]]
}
set ::hd_eco_t0 [clock seconds]
puts "HEAD_ECO_START OT_SLEW_MARGIN $::env(OT_SLEW_MARGIN) OT_SETUP_MARGIN $::env(OT_SETUP_MARGIN) OT_HOLD_MARGIN $::env(OT_HOLD_MARGIN)"
if {![llength [info commands ot_mm_sync]] || ![info exists ::ot_mm_active] || !$::ot_mm_active} {
  error "HEAD_ECO_MODES FAIL: no orfs_hold_mm two-mode session (OT_HOLD_MM=1 + patched load.tcl); refusing a single-mode ECO"
}
if {[ot_mm_sc] ne "tc"} { error "HEAD_ECO_MODES FAIL: setup scene [ot_mm_sc] is not tc (OT_MM_SETUP_CORNER)" }
ot_mm_sync
if {![info exists ::ot_mm_synced] || !$::ot_mm_synced} { error "HEAD_ECO_MODES FAIL: ot_mm_sync did not sync the FF mode" }
read_spef $::env(RESULTS_DIR)/6_final.spef
hd_eco_scene_ws
hd_eco_counts PRE_RCX
ot_hold_structural_gate
source /work/eco_route.tcl
hd_eco_scene_ws
hd_eco_counts POST_GRT_EST
set n 0
foreach i [get_cells -quiet -hierarchical *] { if {[get_property $i ref_name] eq "HB4xp67_ASAP7_75t_R"} { incr n } }
puts "HEAD_ECO_HB4 total $n elapsed_s [expr {[clock seconds] - $::hd_eco_t0}]"
ot_mm_unsync
puts "HEAD_ECO_DONE per-mode (mode ss never carried the FF vclk; the chain installs constraint.sdc as 5_1_grt.sdc)"
