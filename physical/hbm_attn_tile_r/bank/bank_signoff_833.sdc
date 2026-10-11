# idle-sweep-1010: pin-register bank sign-off at 833.333.  Setup: die IO budget 0.2 T in / out (as the route).
# Hold: rule H1 (main ruling 10-10; the earlier flat 0.2 T hold-side IO of f94343374 was masking and is withdrawn):
# input min = sender clk->q min 30 ps (0 wire, conservative until the routed sender views give the measured link min),
# output min 0.  Same lines as bank_hold_h1.sdc, which the IOTIME route appends so hold repair fixes d -> pin flop.
set clk_period 833.333
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_input_delay -min 30 -clock core_clk $non_clock_inputs
set_output_delay -min 0 -clock core_clk [all_outputs]
