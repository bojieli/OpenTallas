# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_pg ck_va ck_vb ck_vc ck_cl ck_ch ck_bt ck_fc ck_fb ck_fv}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {qfd_dv_s8x_vmr} 3 {qfd_dv_s8x_prog} 1 {qfd_dv_s8x_crh} 2 {qfd_dv_s8x_btab} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_dv_slice2_vm8r/clock_entry.sdc
}
