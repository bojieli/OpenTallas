# HBM-ELEM13/HC 10-21 e2_rw14is: MAIN: d/h/e roots, fork at root pin, generic island tool (channel sinks = own island).
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {
  error "E2_SPINE: expected a fresh hybrid CTS wrapper"
}
rename clock_tree_synthesis ot_hci_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
source /src/physical/common_flow/clock_spine_child_ins.tcl
source /src/tools/hbm_hc_clock_1021/e2_write_perimeter_spine.tcl
set ::ot_hci_roots {clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_e0 clk_e1 clk_e2 clk_e3}
set ::ot_hci_skip {clk_w1 clk_w2 clk_w3}
set ::ot_hci_fork root
set ::ot_hci_multi_only 0
set ::ot_hci_tag E2_ISLAND
source /src/tools/hbm_hc_clock_1021/hc_island_spine.tcl
rename clock_tree_synthesis ot_ce_cts_orig
rename ot_hci_hybrid_cts clock_tree_synthesis
puts "E2_SPINE: e2_rw14is island spine fork=root"
