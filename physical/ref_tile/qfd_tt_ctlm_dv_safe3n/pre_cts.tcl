# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_hr}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_qfd_tt_ctlm_static_hr} 1]
set ::ot_ce_landed_raw [dict create {ot_qfd_tt_ctlm_static_hr/ck_pm0} {ref ck_head} {ot_qfd_tt_ctlm_static_hr/ck_pm1} {ref ck_head}]
set ::ot_ce_raw_memory_bindings [dict create {u_gi.g_op.u_leaf.g_op.g_banked.u_rom1} {master ot_rom_4096x72_m8 clock_pin clk root ck_core} {u_gi.g_op.u_leaf.g_op.g_banked.u_rom2} {master ot_rom_4096x72_m8 clock_pin clk root ck_core} {u_gi.g_op.u_leaf.g_op.u_rom} {master ot_rom_4096x72_m8 clock_pin clk root ck_core} {u_gi.u_cal.g_fifo[0].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core} {u_gi.u_cal.g_fifo[1].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core} {u_gi.u_cal.g_fifo[2].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core} {u_gi.u_cal.g_fifo[3].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core} {u_gi.u_cal.g_m[0].u_pm} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core} {u_gi.u_cal.g_m[1].u_pm} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core}]
source /src/physical/common_flow/clock_entries.tcl
set ::ot_lrt_targets [dict create {ot_qfd_tt_ctlm_static_hr/ck_pm0} {ref ck_head tt 287.9 ff 232 ss 379.8} {ot_qfd_tt_ctlm_static_hr/ck_pm1} {ref ck_head tt 288.5 ff 232.5 ss 380.4}]
source /src/physical/common_flow/landed_raw_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tt_ctlm_dv_safe3n/clock_entry.sdc
}
