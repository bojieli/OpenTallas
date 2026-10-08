# Re-sign the preserved 770 ps margin route at the real streaming clock,
# with the current die boundary rather than inferred +63.333 ps slack.
create_clock -name clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
source /src/physical/qwen_slab_structural/io_lat_skew90.sdc
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
