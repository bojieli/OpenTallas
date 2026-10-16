# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck ck_bank0 ck_bank1 ck_bank2 ck_bank3 ck_bank4 ck_bank5 ck_bank6 ck_bank7 ck_bank8 ck_bank9 ck_bank10 ck_bank11 ck_bank12 ck_bank13 ck_bank14 ck_bank15 ck_bank16 ck_bank17 ck_bank18 ck_bank19 ck_bank20 ck_bank21 ck_bank22 ck_bank23}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_sp_res_train_par_0_c1/clock_entry.sdc
}
