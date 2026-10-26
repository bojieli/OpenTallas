source /work/core_density_taps.tcl
source /work/shallow_clock.tcl
ot_dtsh::setup $::dt_blk $::dt_taps $::dt_root $::dt_cell
source /work/hbm_clock_entry.tcl
ot_hbmentry::setup $::dt_blk $::dt_port 20
