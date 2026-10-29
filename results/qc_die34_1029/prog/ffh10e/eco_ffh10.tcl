# DIE-QC-35 PROG QC-020 ffh10e POST_GLOBAL_ROUTE: FF-only post-route hold repair on the ROUTED RC (12.19: measured arrivals
# + 10 ps; same form as the main KV mk_eco b<N> / OT_ECO_FROM=grt ECO: the kit_ffh10 pre-DRT 5_1_grt.odb with its routed
# 6_final.spef).  ffh10 routed FF hold -4.12 / 7 internal reg->reg endpoints (GRT->routed loss 10.44 ps > the 10-ps margin).
# FF frame only (CORNERS bc, vclk = OT_VCLK_FF 381.14 via vclk_corner.tcl); clock frozen + asserted; data-path hold
# buffers only (12.4a a1); no clock ECO / pads / trims.  TT setup is judged by the routed signoff (ffh10 +243.04).
source /work/kit_modes_eco.tcl
read_spef $::env(RESULTS_DIR)/6_final.spef
source /work/clk_freeze.tcl
ot_clk_freeze
puts "ECO_FFH pre FF hold [sta::worst_slack_cmd min] setup(FF) [sta::worst_slack_cmd max]"
global_route -start_incremental
repair_timing -hold -hold_margin 10 -max_buffer_percent 100 -allow_setup_violations
detailed_placement
check_placement -verbose
global_route -end_incremental
ot_clk_freeze_assert eco_ffh10
estimate_parasitics -global_routing
puts "ECO_FFH post (GRT RC) FF hold [sta::worst_slack_cmd min]"
kit_modes_eco_done
ot_vclk_bind tt
source /work/post_grt_pg.tcl
