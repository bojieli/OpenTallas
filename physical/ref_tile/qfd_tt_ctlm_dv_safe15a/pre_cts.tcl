# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_hr}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_qfd_tt_ctlm_static_hr} 1 {qfd_tt_ctlm_dv_wtn} 1]
set ::ot_ce_landed_raw [dict create {ot_qfd_tt_ctlm_static_hr/ck_pm0} {ref ck_head} {ot_qfd_tt_ctlm_static_hr/ck_pm1} {ref ck_head}]
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
set ::ot_sp_child_ins [dict create {ot_qfd_tt_ctlm_static_hr/ck_head} {303.1} {ot_qfd_tt_ctlm_static_hr/ck_pm0} {15.2} {ot_qfd_tt_ctlm_static_hr/ck_pm1} {14.6} {qfd_tt_ctlm_dv_wtn/ck} {141.6}]
source /src/physical/common_flow/domain_spine_child_ins.tcl
source /src/physical/common_flow/domain_spatial_spine.tcl
set ::ot_sp_record_taps_v1 [dict create {version} {1} {model} {hybrid_raw} {records} [dict create {u_hr/ck_pm0} [dict create {instance} {u_hr} {master} {ot_qfd_tt_ctlm_static_hr} {raw} {ck_pm0} {ref} {ck_head} {source_key} {ot_qfd_tt_ctlm_static_hr/ck_pm0} {owner_rule} {same_declared_root} {targets} [dict create {tt} {287.9} {ff} {232.0} {ss} {379.8}] {files} [dict create {results/rtl/ref_tile/qfd_tt_head_static_h16c/qfd_tt_head_static_h16c-h16c-ae6b0c59a/signoff.sdc} {366b2b1bcadd6412d85f2f948833026d29bfcb43d5efde5b1e0fb0946d47d530} {results/closure_loop/qfd_tt_head_static_h16c-h16c-ae6b0c59a/verdict.json} {b3b82118a691aad28cc0e913ae05eb535dbbc7b75f2005f27c2c0b993ee6f562} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/insertion.json} {ffe8b84a9d59ae588ddd62a1f04c5158facfd90a455fcc77a85fe38f670a4277} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr.lef} {7f4ced565455b0641f3e2ed6bc1a49b44b13e7af09a32482351b5366e917c151} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_tt.lib} {84c9bc48dcc9221d527abf015a217036c3e6c2bdb5756fd32f0e76c8205a72c2} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_ff.lib} {5bbf1df917201f6af8074700eca054bb7fc58a159e6af4c740ce8fcdf8dd4acb} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_ss.lib} {dd222a0b697915b505eb9c711f5ce030095289038fdbc288ba17649bd51be45d}]] {u_hr/ck_pm1} [dict create {instance} {u_hr} {master} {ot_qfd_tt_ctlm_static_hr} {raw} {ck_pm1} {ref} {ck_head} {source_key} {ot_qfd_tt_ctlm_static_hr/ck_pm1} {owner_rule} {same_declared_root} {targets} [dict create {tt} {288.5} {ff} {232.5} {ss} {380.4}] {files} [dict create {results/rtl/ref_tile/qfd_tt_head_static_h16c/qfd_tt_head_static_h16c-h16c-ae6b0c59a/signoff.sdc} {366b2b1bcadd6412d85f2f948833026d29bfcb43d5efde5b1e0fb0946d47d530} {results/closure_loop/qfd_tt_head_static_h16c-h16c-ae6b0c59a/verdict.json} {b3b82118a691aad28cc0e913ae05eb535dbbc7b75f2005f27c2c0b993ee6f562} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/insertion.json} {ffe8b84a9d59ae588ddd62a1f04c5158facfd90a455fcc77a85fe38f670a4277} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr.lef} {7f4ced565455b0641f3e2ed6bc1a49b44b13e7af09a32482351b5366e917c151} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_tt.lib} {84c9bc48dcc9221d527abf015a217036c3e6c2bdb5756fd32f0e76c8205a72c2} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_ff.lib} {5bbf1df917201f6af8074700eca054bb7fc58a159e6af4c740ce8fcdf8dd4acb} {physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_ss.lib} {dd222a0b697915b505eb9c711f5ce030095289038fdbc288ba17649bd51be45d}]]]]
source /src/physical/common_flow/spine_record_taps.tcl
set ::ot_lrt_targets [dict create {ot_qfd_tt_ctlm_static_hr/ck_pm0} {ref ck_head tt 287.9 ff 232 ss 379.8} {ot_qfd_tt_ctlm_static_hr/ck_pm1} {ref ck_head tt 288.5 ff 232.5 ss 380.4}]
source /src/physical/common_flow/landed_raw_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tt_ctlm_dv_safe15a/clock_entry.sdc
}
