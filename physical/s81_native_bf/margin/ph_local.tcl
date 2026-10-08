# ORFS PRE_CTS hook for ot_s81_bf_native HALF=1 HALF_PHL=1 (s81-bf, 2026-10-07).
#
# Routed HALF baseline 61c1cf230 failed SS -474.68 ps on ONE path, g_half.ph -> g_half.u_hcg.u_icg/ENA: CTS balanced the
# ungated leaf ph against the gated subtree (93,415 sinks, ~930 ps below the ICG) with 27 delay buffers, so ph launched
# at 1110 ps while the ICG's CLK pin sat at 153 ps.  Under HALF_PHL the phase FF drives only the ICG enable (and its own
# toggle); every clk-domain consumer uses ph_d from balanced leaves (RTL).  This hook moves ph onto the clock net that
# drives the ICG's CLK pin and places it beside the ICG, so the enable launch and the gate share one clock arrival.
# No constraint changes: propagated clocks, the gating check, period and uncertainty are untouched; STA times the real
# arrival.  It runs inside cts.tcl after clock_tree_synthesis and BEFORE the post-CTS repair_timing (wrapping
# repair_timing_helper), so repair and the following detailed_placement see the final netlist.  Fails closed.
#
# Also carries the buffer-cap wrapper of physical/abi3/v41x_karb_repair_buffer_cap.tcl (one PRE_CTS hook per step).
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
source /src/physical/s81_native_bf/margin/ph_local_lib.tcl

if { [info procs repair_timing_helper] ne "" && [info procs ot_phl_inner_repair_timing_helper] eq "" } {
  rename repair_timing_helper ot_phl_inner_repair_timing_helper
  proc repair_timing_helper { args } {
    ot_phl_rewire
    estimate_parasitics -placement
    ot_phl_inner_repair_timing_helper {*}$args
  }
} else {
  error "BF_PHL: repair_timing_helper missing (cts.tcl changed?)"
}
