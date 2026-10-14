# Source-bound observation-only ABI; literal six-master receiver census is in census.py.
# No functional clock/data receiver is driven by fclk_observe in this composition.
# Keep the old generic data-output negative receipt as a separate immutable diagnostic.
unset_output_delay [get_ports fclk_observe]
create_generated_clock -name no3_observe_clk -source [get_ports clk_sm] -divide_by 1 [get_ports fclk_observe]
set_clock_uncertainty -setup 60 [get_clocks no3_observe_clk]
set_clock_uncertainty -hold 25 [get_clocks no3_observe_clk]
set_propagated_clock [get_clocks no3_observe_clk]
puts "NO3_OBSERVATION_ABI literal_clk_sm same_edge divide1 top_output_only external_load80"
