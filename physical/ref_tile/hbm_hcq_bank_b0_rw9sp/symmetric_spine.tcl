# Structural symmetric clock distribution beneath the unchanged hybrid checker.
# The checker still validates every declared root and hard entry before CTS,
# repairs only declared roots, and applies the unmodified timing/spread checks.
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {
  error "B0_SPINE: expected a fresh hybrid CTS wrapper"
}
rename clock_tree_synthesis ot_b0_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
# Read the exact bound hard-view Liberty insertion references. Every selected root is glue-only; all20 independent hard entries keep their
# original delivery and exact raw Liberty paths.
source /src/physical/common_flow/clock_spine_child_ins.tcl
rename clock_tree_synthesis ot_ce_cts_orig
rename ot_b0_hybrid_cts clock_tree_synthesis
puts "B0_SPINE: symmetric29 glue trees beneath unchanged hybrid root/entry checks"
