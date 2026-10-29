# DIE-QC-35 BTAB QC-014 V1d-form POST_GLOBAL_ROUTE (DIE-QC-36 (B); planned repeaters are inserted pre-GRT in pre_b.tcl: try1 inserting them here after read_spef FAILED EST-0104 inconsistent parasitics state): post-route DRV (slew/cap) + hold repair on the V1c ROUTED parasitics
# (6_final.spef of V1c; same warm-ECO form as PROG ffh10r / KV mk_eco OT_ECO_FROM=route b<N>, main 94d520e42): FF-ONLY
# frame (CORNERS bc, OT_HOLD_MM 0, OT_VCLK_CORNER=ff -> vclk = OT_VCLK_FF 202.5), clock frozen + asserted.
# (try1 in the two-mode session FAILED by design: ot_mm_sync re-estimates parasitics on GRT RC, the FIXED clock nets have
#  no GRT route -> FF pin-register mean 140.7 outside 202.5 +- 40; the routed-RC ECO is FF-only, as main mk_eco b.)
# V1c routed: slew TT 11 / FF 2 (worst u_twpd/q[343]/D TT 412.44 / FF 390.95 vs 320: wire-RC slew, TT/FF ratio 1.055),
# FF hold +6.59.  DRV at FF with slew margin 20 (repairs FF > 256 ps ~ TT > 270 ps), hold margin 10 (12.19), data-path
# cells only (12.4a a1); TT setup judged by the routed sign-off (V1c +307.61).  No clock ECO / pads / trims / new check.
source /work/kit_modes_eco.tcl
read_spef /work/v1c_routed.spef
source /work/clk_freeze.tcl
ot_clk_freeze
puts "ECO_B pre (V1c routed RC) setup [sta::worst_slack_cmd max] hold [sta::worst_slack_cmd min]"
report_check_types -max_slew -max_capacitance -violators
global_route -start_incremental
repair_design -slew_margin 20 -cap_margin 10
repair_timing -hold -hold_margin 10 -max_buffer_percent 100 -allow_setup_violations
detailed_placement
check_placement -verbose
global_route -end_incremental
ot_clk_freeze_assert eco_b
estimate_parasitics -global_routing
puts "ECO_B post (GRT RC) setup [sta::worst_slack_cmd max] hold [sta::worst_slack_cmd min]"
report_check_types -max_slew -max_capacitance -violators
kit_modes_eco_done
source /work/grt_post.tcl
