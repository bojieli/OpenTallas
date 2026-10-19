# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_s ck_r0 ck_r1 ck_r2 ck_r3}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hbm_su_static_kind0_lat4_leaf1_physical} 32 {ot_hbm_su_static_bank6_clock_physical} 32]
set ::ot_ce_landed_raw [dict create {ot_hbm_su_static_bank6_clock_physical/clk_macro0} {ref clk_rd} {ot_hbm_su_static_bank6_clock_physical/clk_macro1} {ref clk_rd} {ot_hbm_su_static_bank6_clock_physical/clk_macro2} {ref clk_rd} {ot_hbm_su_static_bank6_clock_physical/clk_macro3} {ref clk_rd} {ot_hbm_su_static_bank6_clock_physical/clk_macro4} {ref clk_rd} {ot_hbm_su_static_bank6_clock_physical/clk_macro5} {ref clk_rd} {ot_hbm_su_static_bank6_clock_physical/clk_ws} {ref clk_rd} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_1} {ref clk_stage_0} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_2} {ref clk_stage_0} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_3} {ref clk_stage_0} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_5} {ref clk_stage_0} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_6} {ref clk_stage_0}]
source /src/physical/common_flow/clock_entries.tcl
set ::ot_lrt_targets [dict create {ot_hbm_su_static_bank6_clock_physical/clk} {ref clk_ws tt 90.3 ff 78.6 ss 106} {ot_hbm_su_static_bank6_clock_physical/clk_macro0} {ref clk_ws tt 141.6 ff 117.6 ss 177.8} {ot_hbm_su_static_bank6_clock_physical/clk_macro1} {ref clk_ws tt 141.3 ff 117.4 ss 177.6} {ot_hbm_su_static_bank6_clock_physical/clk_macro2} {ref clk_ws tt 141.5 ff 117.5 ss 177.7} {ot_hbm_su_static_bank6_clock_physical/clk_macro3} {ref clk_ws tt 130.5 ff 106.1 ss 167.1} {ot_hbm_su_static_bank6_clock_physical/clk_macro4} {ref clk_ws tt 127.7 ff 103.2 ss 164.3} {ot_hbm_su_static_bank6_clock_physical/clk_macro5} {ref clk_ws tt 130.1 ff 105.7 ss 166.7} {ot_hbm_su_static_bank6_clock_physical/clk_rd} {ref clk_ws tt 66.2 ff 59.8 ss 72.9} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_1} {ref clk_stage_0 tt 47.2 ff 35 ss 68.5} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_2} {ref clk_stage_0 tt 34.5 ff 28 ss 47} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_3} {ref clk_stage_0 tt 43.8 ff 32.4 ss 64.4} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_5} {ref clk_stage_0 tt 22.5 ff 17.3 ss 34.2} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_6} {ref clk_stage_0 tt 43.9 ff 34.1 ss 63.6} {ot_hbm_su_static_kind0_lat4_leaf1_physical/clk_stage_7} {ref clk_stage_0 tt 66.1 ff 52.6 ss 92}]
source /src/physical/common_flow/landed_raw_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_su_pgslice_lg_light_d4g/clock_entry.sdc
}
