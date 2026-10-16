# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {clk_ctl clk_red clk_rf[0] clk_rf[1] clk_rf[2] clk_rf[3] clk_rf[4] clk_rf[5] clk_rf[6] clk_rf[7] clk_rf[8] clk_rf[9] clk_rf[10] clk_rf[11] clk_rf[12] clk_rf[13] clk_rf[14] clk_rf[15] clk_rf[16] clk_rf[17] clk_rf[18] clk_rf[19] clk_rf[20] clk_rf[21] clk_rf[22] clk_rf[23] clk_rf[24] clk_rf[25] clk_rf[26] clk_rf[27] clk_rf[28] clk_rf[29] clk_rf[30] clk_rf[31] clk_rf[32] clk_rf[33] clk_rf[34] clk_rf[35] clk_rf[36] clk_rf[37] clk_rf[38] clk_rf[39] clk_rf[40] clk_rf[41] clk_rf[42] clk_rf[43] clk_rf[44] clk_rf[45] clk_rf[46] clk_rf[47] clk_rf[48] clk_rf[49] clk_rf[50] clk_rf[51] clk_rf[52] clk_rf[53] clk_rf[54] clk_rf[55] clk_rf[56] clk_rf[57] clk_rf[58] clk_rf[59] clk_rf[60] clk_rf[61] clk_rf[62] clk_rf[63]}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_qcore_s_pinrung_r1/clock_entry.sdc
}
