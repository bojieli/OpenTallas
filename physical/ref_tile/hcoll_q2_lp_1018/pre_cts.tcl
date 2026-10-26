# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_sw ck_wr ck_rg}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hgi_coll_ctl_v5_q2} 1 {ot_hgi_coll_fj_q2} 1 {ot_hgi_coll_qslots_capture_pin_v2} 9 {ot_hgi_coll_qso_q2_b32} 17 {ot_hgi_coll_qso_q2_b1} 1 {ot_hgi_coll_static_vmwrite_roots_v6_physical} 1 {ot_hgi_coll_pring_static_state_capture_lane} 8 {ot_hgi_coll_ring_ag_ctl} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hcoll_q2_lp_1018/clock_entry.sdc
}
