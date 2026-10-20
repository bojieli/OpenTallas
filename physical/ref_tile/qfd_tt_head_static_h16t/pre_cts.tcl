# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_head ck_pm0 ck_pm1}
set ::ot_ce_raw_memory_bindings [dict create {u_22617} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_pm0} {u_22618} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_pm1} {u_22619} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_pm0} {u_22620} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_pm0} {u_22621} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_pm0} {u_22622} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_pm0} {u_22623} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_pm1} {u_22624} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_pm1}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tt_head_static_h16t/clock_entry.sdc
}
