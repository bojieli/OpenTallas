# PQ screen composition sign-off at 833.333 ps (el1011-ds-misc/pqc): core_clk + the vclk IO of
# physical/s81_pq_hier/compose/sdc/io_vclk.sdc (no boundary registers at the top level; see that file).
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [get_clocks core_clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
create_clock -name vclk -period 833.333
set_clock_latency 270 [get_clocks vclk]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
set_input_delay -max 300 -clock vclk $ot_in
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -max 300 -clock vclk [all_outputs]
set_output_delay -min -150 -clock vclk [all_outputs]
