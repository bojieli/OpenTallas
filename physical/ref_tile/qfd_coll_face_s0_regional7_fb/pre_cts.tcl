# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {cal_ck tx_wck rx_rck cal_lck tx_rck rx_wck codec0 codec1 codec2 codec3 codec4 codec0p}
set ::ot_ce_raw_memory_bindings [dict create {u_body.g_codec_pl.u_codec.g_bank[0].g_local.u_store.u_sram} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root codec1} {u_body.g_codec_pl.u_codec.g_bank[1].g_local.u_store.u_sram} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root codec2} {u_body.g_codec_pl.u_codec.g_bank[2].g_local.u_store.u_sram} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root codec3} {u_body.g_codec_pl.u_codec.g_bank[3].g_local.u_store.u_sram} {master ot_sram_1r1w_64x512_m1_r2c2 clock_pin clk root codec4} {u_body.u_rx.u_mem} {master ot_sram_1r1w2c_64x546_m1 clock_pins {rclk rx_rck wclk rx_wck}} {u_body.u_tx.u_mem} {master ot_sram_1r1w2c_64x546_m1 clock_pins {rclk tx_rck wclk tx_wck}}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_coll_face_s0_regional7_fb/clock_entry.sdc
}
