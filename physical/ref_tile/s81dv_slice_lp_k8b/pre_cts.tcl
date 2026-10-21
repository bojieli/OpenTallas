# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_C ck_L0 ck_L1 ck_L3 ck_L4}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_s81sl_vp} 5 {ot_s81sl_vn} 5 {ot_s81sl_ve} 5 {ot_s81sl_vsw} 5 {ot_s81sl_vq} 5 {ot_s81sl_vs} 5 {dsfd_su_t_rxsf} 5 {dsfd_su_t_rxsb} 5 {ot_s81sl_xg5} 1 {ot_s81sl_capc2} 1 {ot_s81dv_xfin} 1 {ot_s81sl_xr1} 1 {ot_s81sl_eg} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81dv_slice_lp_k8b/clock_entry.sdc
}
