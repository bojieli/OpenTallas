# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_r_io ck_r_cl ck_r_ch ck_r_bt ck_r_pg ck_r_va ck_r_vb ck_r_vc}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {qfd_dv_s8x_crh} 2 {qfd_dv_s8x_btab} 1 {qfd_dv_s8x_prog} 1 {qfd_dv_s8x_vmr} 3]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_dv_slice2_vm8lh/clock_entry.sdc
}
