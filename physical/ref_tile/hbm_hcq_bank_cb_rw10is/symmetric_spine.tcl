# HBM-ELEM13/HC 10-21 cb_rw10is: MAIN: all glue roots rebuilt; fork outside macros at island x-midpoint (equal trunks).
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {
  error "CB_SPINE: expected a fresh hybrid CTS wrapper"
}
rename clock_tree_synthesis ot_hci_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
source /src/physical/common_flow/clock_spine_child_ins.tcl
set ::ot_hci_roots {clk clk_c clk_o clk_w0 clk_w1 clk_w2 clk_w3 clk_x0 clk_x1 clk_x2 clk_x3 clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_f clk_e0 clk_e1 clk_e2 clk_e3 clk_i0 clk_i1 clk_i2 clk_i3 clk_q0 clk_q1 clk_q2 clk_q3}
set ::ot_hci_skip {}
set ::ot_hci_fork mid
set ::ot_hci_multi_only 0
set ::ot_hci_tag CB_ISLAND
source /src/tools/hbm_hc_clock_1021/hc_island_spine.tcl
rename clock_tree_synthesis ot_ce_cts_orig
rename ot_hci_hybrid_cts clock_tree_synthesis
puts "CB_SPINE: cb_rw10is island spine fork=mid multi_only=0 beneath unchanged hybrid root/entry checks"
