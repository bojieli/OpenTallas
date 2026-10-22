# HBM-ELEM13/HC-QHUB 10-21: planned equal-depth spine owns glue root clk (single) beneath the UNCHANGED hybrid
# entry/root checks (clock_entries.tcl wrapper, OT_HYBRID CLOCK_RULE, raw SRAM binding). Kit pre_cts_extra.
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {error "QHUB_SPINE: expected a fresh hybrid CTS wrapper"}
rename clock_tree_synthesis ot_qh_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
source /src/physical/common_flow/clock_spine.tcl
set ::ot_qh_mode single
source /src/tools/hbm_hc_clock_1021/qhub_regional_spine.tcl
rename clock_tree_synthesis ot_ce_cts_orig
rename ot_qh_hybrid_cts clock_tree_synthesis
puts "QHUB_SPINE: single spine for clk beneath unchanged hybrid root/entry checks"
