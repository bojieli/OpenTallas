# Four planned islands stay blocked through density-tap DPL; release only for clock planner.
source /work/clock_islands.tcl
source /work/hold_budget.tcl
source /work/base_core_density_taps.tcl
ot_e5_clock_islands release
source /work/shallow_clock.tcl
ot_dtsh::setup $::dt_blk $::dt_taps $::dt_root $::dt_cell
