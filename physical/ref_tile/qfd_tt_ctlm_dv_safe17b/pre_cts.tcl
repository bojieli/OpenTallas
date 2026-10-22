# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_hr}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_qfd_tt_ctlm_static_hr_safe32_native32_1r} 1 {qfd_tt_ctlm_dv_wtn} 1]
set ::ot_ce_raw_memory_bindings [dict create {u_gi.g_op.u_leaf.g_op.g_banked.u_rom1} {master ot_rom_4096x72_m8 clock_pin clk root ck_core} {u_gi.g_op.u_leaf.g_op.g_banked.u_rom2} {master ot_rom_4096x72_m8 clock_pin clk root ck_core} {u_gi.g_op.u_leaf.g_op.u_rom} {master ot_rom_4096x72_m8 clock_pin clk root ck_core} {u_gi.u_cal.g_calrom.u_rom.m0} {master ot_rom_4096x266_m8 clock_pin clk root ck_core} {u_gi.u_cal.g_calrom.u_rom.m1} {master ot_rom_4096x266_m8 clock_pin clk root ck_core} {u_gi.u_cal.g_m[0].u_pm.u_p192} {master ot_sram_1r1w_64x512_m1_r2c2_p192_mir clock_pin clk root ck_core} {u_gi.u_cal.g_m[1].u_pm.u_p192} {master ot_sram_1r1w_64x512_m1_r2c2_p192_mir clock_pin clk root ck_core}]
# Explicit per-domain spatial spine; existing clock-entry timing is unchanged.
foreach name [array names ::env OT_SPINE*] {unset ::env($name)}
set ::env(OT_SPINE_PORTS) {ck_core,ck_hr}
set ::env(OT_SPINE_SYM) {1}
set ::env(OT_SPINE_RC_CAL) {0}
set ::env(OT_SPINE_BIN) {30}
set ::env(OT_SPINE_LEAF_N) {16}
set ::env(OT_SPINE_ITERS) {10}
set ::env(OT_SPINE_MACRO_LEAF) {1}
set ::env(OT_SPINE_MACRO_PIN_LEAF) {1}
set ::ot_dsp_roots {ck_core ck_hr}
source /src/physical/common_flow/clock_spine.tcl
source /src/physical/common_flow/clock_entries.tcl
# SQ-TTC4 10-21: hard-child clock-pin leaves balanced at pin + the child record insertion (child flops)
set ::ot_sp_child_ins [dict create {ot_qfd_tt_ctlm_static_hr_safe32_native32_1r/ck_head} {480.5} {qfd_tt_ctlm_dv_wtn/ck} {141.6}]
source /src/physical/common_flow/domain_spine_child_ins.tcl
source /src/physical/common_flow/domain_spatial_spine.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tt_ctlm_dv_safe17b/clock_entry.sdc
}
