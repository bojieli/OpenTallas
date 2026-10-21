# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_rt ck_cw ck_ce ck_rn ck_rs}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_s81sl_cap_rt} 1 {ot_s81sl_cap_tr} 2 {ot_s81sl_cap_ed} 1 {ot_s81sl_cap_ld} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81sl_capc5r/clock_entry.sdc
}

# DRIVE-S81-CAP: post-CTS region latency balance
set ::ot_rtb_regions {{ot_entry_0 {{u_rt/clk 266.15 31.85}}}}
source /src/physical/ref_tile/s81sl_capc5r/rt_leaf_balance.tcl
