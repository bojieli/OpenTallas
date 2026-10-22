# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_tx ck_sr ck_rxo ck_dec ck_prx}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_s81_kp4_dsyn} 1 {ot_s81_kp4_ddly} 1 {ot_s81_kp4_dchn} 1 {ot_s81_kp4_dout} 1 {ot_s81_kp4_enc} 1]
set ::ot_ce_raw_memory_bindings [dict create {u_prx} {master ot_s81_pma_rxn clock_pin pma_rck root ck_prx} {u_ptx} {master ot_s81_pma_txm clock_pin ck root ck_tx} {u_rmm} {master ot_sram_1r1w2c_16x546_m1 clock_pins {rclk ck_rxo wclk ck_dec}}]
set ::env(OT_SPINE_PORTS) {ck_tx,ck_sr,ck_rxo,ck_dec,ck_prx}
set ::env(OT_SPINE_CTS_REST) 0
source /src/physical/common_flow/clock_spine.tcl
set ::env(OT_SPINE_MACRO_LEAF) 1
set ::env(OT_SPINE_MACRO_PIN_LEAF) 1
source /src/physical/ref_tile/s81lk_serdes_col_sp10a/spine_ins.tcl
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81lk_serdes_col_sp10a/clock_entry.sdc
}
