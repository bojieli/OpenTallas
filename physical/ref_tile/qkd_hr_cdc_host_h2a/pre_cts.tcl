# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_host}
set ::ot_ce_raw_memory_bindings [dict create {u_rank__u_bridge__u_done.g_afw.u_af.g_mm.g_pad32.u_m} {master ot_sram_1r1w2c_32x546_m1_p192_mir clock_pins {rclk ck_core wclk ck_host}} {u_rank__u_bridge__u_done.g_ib_mem.g_32.u_ib} {master ot_sram_1r1w_32x546_m1_p192_mir clock_pin clk root ck_host} {u_rank__u_bridge__u_ing.g_afw.u_af.g_mm.g_pad32.u_m} {master ot_sram_1r1w2c_32x546_m1_p192_mir clock_pins {rclk ck_host wclk ck_core}} {u_rank__u_bridge__u_ing.g_ib_mem.g_32.u_ib} {master ot_sram_1r1w_32x546_m1_p192_mir clock_pin clk root ck_core} {u_rank__u_fence.g_on.u_queue} {master ot_sram_1r1w_32x64_m1_p192_mir clock_pin clk root ck_host}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qkd_hr_cdc_host_h2a/clock_entry.sdc
}
