# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_host ck_ingest}
set ::ot_ce_raw_memory_bindings [dict create {u_ot_pr_core.u_rank__u_qm.u_cxm} {master ot_sram_1r1w2c_32x546_m1_p192_mir clock_pins {rclk ck_host wclk ck_ingest}} {u_ot_pr_core.u_rank__u_qm.u_hxm} {master ot_sram_1r1w2c_32x546_m1_p192_mir clock_pins {rclk ck_ingest wclk ck_host}} {u_ot_pr_core.u_rank__u_qm.u_oxm} {master ot_sram_1r1w2c_32x546_m1_p192_mir clock_pins {rclk ck_core wclk ck_ingest}}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qkd_hr_ingest_shell_s3b/clock_entry.sdc
}
