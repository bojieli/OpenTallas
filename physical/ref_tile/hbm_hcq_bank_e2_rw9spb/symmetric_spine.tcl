# Structural symmetric clock distribution beneath the unchanged hybrid checker.
# The checker still validates every declared root and hard entry before CTS,
# repairs only declared roots, and applies the unmodified timing/spread checks.
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {
  error "E2_SPINE: expected a fresh hybrid CTS wrapper"
}
rename clock_tree_synthesis ot_e2_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
# Read the exact bound hard-view Liberty insertion references. The selected clk
# root is glue-only; all independent hard entries keep their original delivery.
source /src/physical/common_flow/clock_spine_child_ins.tcl
rename clock_tree_synthesis ot_ce_cts_orig
rename ot_e2_hybrid_cts clock_tree_synthesis
puts "E2_SPINE: symmetric clk tree beneath unchanged hybrid root/entry checks"
