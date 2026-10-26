# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core[0] ck_hr[0]}
set ::ot_ce_raw_memory_bindings [dict create {u_gi.g_op.u_leaf.g_op.g_banked.u_rom1} {master ot_rom_4096x72_m8 clock_pin clk root ck_core[0]} {u_gi.g_op.u_leaf.g_op.g_banked.u_rom2} {master ot_rom_4096x72_m8 clock_pin clk root ck_core[0]} {u_gi.g_op.u_leaf.g_op.u_rom} {master ot_rom_4096x72_m8 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_calrom.u_rom.m0} {master ot_rom_4096x266_m8 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_calrom.u_rom.m1} {master ot_rom_4096x266_m8 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_fifo[0].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_fifo[1].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_fifo[2].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_fifo[3].u_fifo} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_m[0].u_pm} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core[0]} {u_gi.u_cal.g_m[1].u_pm} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_core[0]} {u_hr.u_24525} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_hr[0]} {u_hr.u_24526} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root ck_hr[0]} {u_hr.u_24527} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_hr[0]} {u_hr.u_24528} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_hr[0]} {u_hr.u_24529} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_hr[0]} {u_hr.u_24530} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_hr[0]} {u_hr.u_24531} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_hr[0]} {u_hr.u_24532} {master ot_sram_1r1w_32x128_m1 clock_pin clk root ck_hr[0]}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_hp13_cpub39_full_main/clock_entry.sdc
}
