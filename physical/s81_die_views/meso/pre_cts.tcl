# CLAUDE S81-RERUN meso view PRE_CTS: the virtual IO clocks take each tree's measured insertion BEFORE the CTS-stage
# repair (the S81-PH vclk_latency.tcl wrapper): with the planning latency the calibration run's hold repair padded
# every r_d output (-86 ps, RSZ-0060 at 7,443 buffers).  POST_CTS re-measures after the repair.
set ::ot_meso_pre 1
source /src/physical/s81_die_views/meso/post_cts_vclk.tcl
unset ::ot_meso_pre
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
if { [info procs repair_timing_helper] ne "" && [info procs ot_m_repair_timing_helper] eq "" } {
  rename repair_timing_helper ot_m_repair_timing_helper
  proc repair_timing_helper { args } {
    ot_meso_vclk
    ot_m_repair_timing_helper {*}$args
  }
}
