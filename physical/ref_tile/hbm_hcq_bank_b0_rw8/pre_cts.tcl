# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {clk clk_c clk_o clk_w0 clk_w1 clk_w2 clk_w3 clk_x0 clk_x1 clk_x2 clk_x3 clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_e0 clk_e1 clk_e2 clk_e3 clk_q0 clk_q1 clk_q2 clk_q3 clk_s0 clk_s1}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_hcq_bank_b0_rw8/clock_entry.sdc
}
