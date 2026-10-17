# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck ck_bank[0] ck_bank[1] ck_bank[2] ck_bank[3] ck_bank[4] ck_bank[5] ck_bank[6] ck_bank[7] ck_bank[8] ck_bank[9] ck_bank[10] ck_bank[11] ck_bank[12] ck_bank[13] ck_bank[14] ck_bank[15] ck_bank[16] ck_bank[17] ck_bank[18] ck_bank[19] ck_bank[20] ck_bank[21] ck_bank[22] ck_bank[23]}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_res_train_half_b2_4_1016/clock_entry.sdc
}
