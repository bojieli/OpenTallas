# PLAN TIMING AUDIT 11-15 (tools/die_plan/plan_timing_audit.py, branch claude/plan-timing-audit-1115 @46ea41ce53, hub + GitHub)

Reach (a): 0 failing lanes on all four dies (plan-lane geometry is capped at 405 um by G0 hops; the S2 failures are kit-side). Core boundary (b): measured pin-register depth (signed-run flop CK arrivals) vs type budget. FAIL = no early tap and depth > budget-50, or early tap declared vs measured > tol, or clk->q + setup leave < 150 ps of 833. UNMEASURED = no attributable measurement (never a failure); LIB = liberty max_clock_tree_path fallback.

## S81 (B6e0, after shared-dir fix)
`{"reach_failing_lanes": 0, "core_rows": {"PASS": 3972, "UNMEASURED": 954, "FAIL": 257}, "failing_types": 247, "unmeasured_rows": 954, "unmeasured_types": 298, "unmeasured_instances": 9783, "unmeasured_lib_would_fail": 222, "core_types": 346, "worst_reach_over_ps": 0.0, "worst_core_over_ps": 427.1}`

failing types 247; worst 20:

type | module | depth | budget | over | tap | arc headroom | reason
--|--|--|--|--|--|--|--
bk_sel__t2 | dsdv_idx_tx_n32 | 677.1 | 250.0 | 427.1 | early | -181.1 | early tap declares 829 ps, measured depth 677 ps (|d| 152 > tol 40); boundary arcs clk->q 1014 + setup 0 = 101
dsdv_slice_c1x_C__t10 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
dsdv_slice_iq_C__t1 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
dsdv_slice_kv512_C__t1 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
dsdv_slice_c3x_C__t1 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
dsdv_slice_c1x_C__t6 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
dsdv_slice_lepe_nh_mus_C__t1 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
dsdv_slice_lepe_mu_C__t1 | ot_s81sl_capc5r | 271.4 | 250.0 | 21.4 | grid | 375.4 | core clock depth 271 ps > budget 250 - 50 with no early tap
svc_lo_dsdv_svc_rs_w__t1 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_hi_dsdv_svc_rs__t1 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_lo_dsdv_svc_rs__t1 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_hi_dsdv_svc_rs__t2 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_lo_dsdv_svc_rs__t2 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_hi_dsdv_svc_pvso_entry__t1 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_lo_dsdv_svc_rs__t3 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_hi_dsdv_svc_rs__t3 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_lo_dsdv_svc_rs__t4 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_hi_dsdv_svc_rs__t4 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_lo_dsdv_svc_rs__t5 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap
svc_hi_dsdv_svc_pvso_entry__t2 | dsdv_svc_sx_hrow | 268.9 | 250.0 | 18.9 | grid | 379.3 | core clock depth 269 ps > budget 250 - 50 with no early tap

## QC (S4d)
`{"reach_failing_lanes": 0, "core_rows": {"FAIL": 32, "UNMEASURED": 247, "PASS": 48}, "failing_types": 28, "unmeasured_rows": 247, "unmeasured_types": 50, "unmeasured_instances": 594, "unmeasured_lib_would_fail": 14, "core_types": 82, "worst_reach_over_ps": 0.0, "worst_core_over_ps": 524.4}`

failing types 28; worst 20:

type | module | depth | budget | over | tap | arc headroom | reason
--|--|--|--|--|--|--|--
cbx_q10__cl94a12200 | qfd_tile_nl_a0c | 774.4 | 250.0 | 524.4 | early | -105.1 | boundary arcs clk->q 938 + setup 0 = 938 ps leave -105 ps of 833 for wire (< 150)
cbx_q10__cl89936551 | qfd_tile_nl_a0c | 774.4 | 250.0 | 524.4 | early | -105.1 | boundary arcs clk->q 938 + setup 0 = 938 ps leave -105 ps of 833 for wire (< 150)
cbx_q10__cl89936551_h | qfd_tile_nl_a0c | 774.4 | 250.0 | 524.4 | early | -105.1 | boundary arcs clk->q 938 + setup 0 = 938 ps leave -105 ps of 833 for wire (< 150)
cbx_q10__cl94a12200_h | qfd_tile_nl_a0c | 774.4 | 250.0 | 524.4 | early | -105.1 | boundary arcs clk->q 938 + setup 0 = 938 ps leave -105 ps of 833 for wire (< 150)
cbf_q01 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbf_q11 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbf_q01_s2 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbf_q00_s2 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q00__cld7bf7197 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q00__cl622f65d2 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q00__cldbcda913 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q01__cldd6ea846 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q01__clab6e67f2 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q01__cld9ff4c40 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q11__cl5cc92dfe | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbn_q11__cl49ae4555 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbf_q00__cl1b5a6458 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
cbf_q00__cl870de686 | qfd_tile_nk_a0c | 733.2 | 250.0 | 483.2 | early | -90.2 | boundary arcs clk->q 923 + setup 0 = 923 ps leave -90 ps of 833 for wire (< 150)
slw_sc_v2 | qfd_dv_s5_sc2_leaf | 406.4 | 250.0 | 156.4 | early | 292.2 | early tap declares 335 ps, measured depth 406 ps (|d| 71 > tol 40)
sle_sc_v2 | qfd_dv_s5_sc2_leaf | 406.4 | 250.0 | 156.4 | early | 292.2 | early tap declares 335 ps, measured depth 406 ps (|d| 71 > tol 40)

## HEAD (rp21z20)
`{"reach_failing_lanes": 0, "core_rows": {"PASS": 3, "UNMEASURED": 11, "FAIL": 2}, "failing_types": 2, "unmeasured_rows": 11, "unmeasured_types": 6, "unmeasured_instances": 235, "unmeasured_lib_would_fail": 0, "core_types": 7, "worst_reach_over_ps": 0.0, "worst_core_over_ps": -18.0}`

failing types 2; worst 20:

type | module | depth | budget | over | tap | arc headroom | reason
--|--|--|--|--|--|--|--
hd_host_e | ot_s81hd_he_epc | 432.0 | 450.0 | -18.0 | early | -594.5 | early tap declares 350 ps, measured depth 432 ps (|d| 82 > tol 40); boundary arcs clk->q 1075 + setup 353 = 14
hd_serdes | ot_s81_kp4_dchn | 288.5 | 450.0 | -161.5 | grid | 73.5 | boundary arcs clk->q 450 + setup 310 = 760 ps leave 73 ps of 833 for wire (< 150)

## KV (kvgeom6 plan_c)
`{"reach_failing_lanes": 0, "core_rows": {"PASS": 167, "UNMEASURED": 34}, "failing_types": 0, "unmeasured_rows": 34, "unmeasured_types": 10, "unmeasured_instances": 75, "unmeasured_lib_would_fail": 0, "core_types": 45, "worst_reach_over_ps": 0.0, "worst_core_over_ps": 0.0}`

failing types 0; worst 20:

type | module | depth | budget | over | tap | arc headroom | reason
--|--|--|--|--|--|--|--
