# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_rck}
set ::ot_ce_raw_memory_bindings [dict create {u_prx} {master ot_ucie_pma_rxm clock_pin pma_rck root ck_rck} {u_ptx} {master ot_ucie_pma_txm clock_pin ck root ck_core} {u_rmm} {master ot_sram_1r1w2c_16x546_m1 clock_pins {rclk ck_core wclk ck_rck}}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_pdie_ucie_col/clock_entry.sdc
}
