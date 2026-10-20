# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {clk clk_n clk_s clk_e clk_w}
set ::ot_ce_raw_memory_bindings [dict create {u_ot_pr_core.bank.u_a} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root clk} {u_ot_pr_core.bank.u_a1} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root clk} {u_ot_pr_core.bank.u_b} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root clk} {u_ot_pr_core.bank.u_c} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root clk}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hnx_vms_bank_safe3/clock_entry.sdc
}
