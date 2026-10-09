# Intrinsic ETM characterization only; this is not an R25I boundary budget.
# Preserve raw routed leaf SDC/corner results separately. Zero external delays
# expose the native pin arcs without leaf virtual-IO exceptions or assumed
# shared arrival/insertion. Accepted by hbm_wiring 2026-10-09.
create_clock -name core_clk -period 833.333333333 [get_ports ck]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay -max 0 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 0 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
