# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {cw cr}
set ::ot_ce_raw_memory_bindings [dict create {u_ring.g_bank[0].u_mem} {master ot_sram_1r1w2c_64x516_m1 clock_pins {rclk cr wclk cw}} {u_ring.g_bank[1].u_mem} {master ot_sram_1r1w2c_64x516_m1 clock_pins {rclk cr wclk cw}} {u_ring.g_bank[2].u_mem} {master ot_sram_1r1w2c_64x516_m1 clock_pins {rclk cr wclk cw}}]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hidx_land1210_face_main_1021/clock_entry.sdc
}
