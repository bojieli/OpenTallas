# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_tx ck_ptx ck_syn ck_dly ck_chn ck_out}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_s81_kp4_dsyn} 1 {ot_s81_kp4_ddly} 1 {ot_s81_kp4_dchn} 1 {ot_s81_kp4_dout} 1 {ot_s81_kp4_enc} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81lk_serdes_col_lp/clock_entry.sdc
}
