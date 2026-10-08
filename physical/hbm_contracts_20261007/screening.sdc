# Screening envelope for the HBM contract blocks (no budget sheet exists for these new masters).
# Registered boundary assumed on the far side: 20 % of the 833.333 ps period each way (166.67 ps).
# ASAP7 native units: ps and fF.  Clock and uncertainties supplied by the driver (60 setup / 25 hold).
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_input_delay -max 166.6666 -clock core_clk [all_inputs -no_clocks]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_output_delay -max 166.6666 -clock core_clk [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
set_load 80 [all_outputs]
