# Qwen ROM decode core sign-off at the real 833.333 ps for routes over-constrained at 770 (closure-loop verdict and
# hold-ECO post-SDC): core_clk re-created at 833.333, propagated, 60 / 25 ps uncertainty, then the die-context boundary
# (io_ref_skew.sdc with OT_IO_SKEW 90: every core port is intra-region; hold allowance 50).
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ::env(OT_IO_SKEW) 90
set ::env(OT_IO_HOLD_SKEW) 50
source /src/physical/qwen_core_ctx/io_ref_skew.sdc
