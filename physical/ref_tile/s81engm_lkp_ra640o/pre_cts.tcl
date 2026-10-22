# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck ck_hash[0] ck_hash[1] ck_hash[2] ck_hash[3] ck_hash[4] ck_hash[5] ck_seed ck_n ck_s ck_rd}
set ::ot_ce_raw_memory_bindings [dict create {u_e.u_row_a} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root ck_rd} {u_e.u_row_e} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root ck_rd} {u_e.u_row_o} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root ck_rd}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81engm_lkp_ra640o/clock_entry.sdc
}
