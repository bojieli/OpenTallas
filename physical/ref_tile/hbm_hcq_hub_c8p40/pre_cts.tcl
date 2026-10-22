# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {clk}
set ::ot_ce_raw_memory_bindings [dict create {u_q.g_qcal.programme.u_program} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root clk}]
source /src/physical/common_flow/clock_entries.tcl
source /src/tools/hbm_hc_clock_1021/qhub_spine_quad.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_hcq_hub_c8p40/clock_entry.sdc
}
