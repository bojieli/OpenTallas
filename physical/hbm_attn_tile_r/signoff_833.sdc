# H16 quad parent sign-off at 833.333 ps (OWNER RULE 2026-10-06 ADDENDUM): the route is over-constrained (770 ps);
# corner_sta --post-sdc re-times the routed tile at the real period.  IO budget: 300 ps each way = >= 150 ps die
# clock-arrival difference + 150 ps wire to the nearest die station; every pin is flop-direct.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
set_input_delay 300 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay 300 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
