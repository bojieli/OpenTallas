# idle-sweep-1010: pin-register bank sign-off at 833.333 with the die IO budget the route used (run_abi3_physical
# --io-delay-fraction 0.2: set_input_delay / set_output_delay 0.2 T, the same value for setup and hold, as every
# route_view die block).  bank_interface.sdc (the [att] ETM extraction SDC) sets the hold-side IO delays to 0, which no
# other die block signs off against; with it the bank showed FF -63..-102 ps on d -> pin flop only (route SDC +90).
set clk_period 833.333
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
