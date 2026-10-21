# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {stream_clk hbm_clk}
set ::ot_ce_raw_memory_bindings [dict create {feed.producer.ordinal_bank[0].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[1].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[2].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[3].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[4].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[5].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[6].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.producer.ordinal_bank[7].u_bank.u_payload} {master ot_sram_1r1w_256x256_m2_r2c2 clock_pin clk root stream_clk} {feed.programme_leaf.g_m2.u_program_hi} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root stream_clk} {feed.programme_leaf.g_m2.u_program_lo} {master ot_sram_1r1w_1024x256_m2_r2c2 clock_pin clk root stream_clk} {feed.rows.g_cache[0].u_payload} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk} {feed.rows.g_cache[1].u_payload} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk} {feed.rows.g_cache[2].u_payload} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk} {feed.rows.g_cache[3].u_payload} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk} {feed.rows.g_cache[4].u_payload} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk} {issuer.g_t2.u_desc_hi} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk} {issuer.g_t2.u_desc_lo} {master ot_sram_1r1w_128x256_m1_r2c2 clock_pin clk root stream_clk}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hdie_svg_rel8b/clock_entry.sdc
}
