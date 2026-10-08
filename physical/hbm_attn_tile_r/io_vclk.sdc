# H16 quad parent IO budget (OWNER RULE 2026-10-06 ADDENDUM): the die clock reaches the neighbouring die flops at about
# this tile's own insertion (measured on the PMID 0 parent p1: register clock pins ~1,350 ps after clk), so IO is timed
# against a virtual clock carrying that latency, with 300 ps max each way (>= 150 ps clock-arrival difference + 150 ps
# wire to the nearest die station) and -150 ps min (the same arrival difference, early).  Replaces the core_clk IO delays.
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_latency 1350 [get_clocks vclk]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay -max 300 -clock vclk $ot_in
set_input_delay -min -150 -clock vclk $ot_in
set_output_delay -max 300 -clock vclk [all_outputs]
set_output_delay -min -150 -clock vclk [all_outputs]
