# HBM-ELEM13/HC 10-21 rw13isb: rw12is spine chain (w1 perimeter + w2/w3 write) + per-island equal-depth subtrees.
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {
  error "E2_SPINE: expected a fresh hybrid CTS wrapper"
}
rename clock_tree_synthesis ot_e2_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
source /src/physical/common_flow/clock_spine_child_ins.tcl
source /src/tools/hbm_hc_clock_1021/e2_write_perimeter_spine.tcl
set ::ot_e2_island_roots {clk clk_c clk_ce clk_w0 clk_w1 clk_w2 clk_w3 clk_x0 clk_x1 clk_x2 clk_x3 clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_e0 clk_e1 clk_e2 clk_e3}
source /src/tools/hbm_hc_clock_1021/e2_allroot_island_spine.tcl
rename clock_tree_synthesis ot_ce_cts_orig
rename ot_e2_hybrid_cts clock_tree_synthesis
puts "E2_SPINE: rw13isb island subtrees for {$::ot_e2_island_roots} beneath unchanged hybrid root/entry checks"
